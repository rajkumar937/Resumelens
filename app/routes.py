"""
routes.py — Flask routes for ResumeLens Stage 9.
Security hardened: unique tmp filenames, JD size cap, safe score storage,
no stack traces to client, structured logging.
"""

import os
import uuid
import logging
from flask import (
    Blueprint, render_template, request, jsonify,
    redirect, url_for, flash, current_app, send_from_directory,
)
from werkzeug.utils import secure_filename

from .extractor import extract_text_by_page, extract_resume_info
from .skills import extract_skills, match_skills
from .matcher import compute_match_score
from . import database as db

bp = Blueprint("main", __name__)
log = logging.getLogger(__name__)


def _allowed_file(filename: str) -> bool:
    allowed = current_app.config.get("ALLOWED_EXTENSIONS", {"pdf"})
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in allowed
    )


def _safe_float(value, default: float = 0.0) -> float:
    """Convert to float safely; returns default for None/invalid."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ── Main page ─────────────────────────────────────────────
@bp.route("/")
def index():
    return render_template("index.html")


# ── PWA ───────────────────────────────────────────────────
@bp.route("/offline")
def offline():
    return render_template("offline.html")


@bp.route("/sw.js")
def service_worker():
    # Served from root (not /static/) so its scope covers the whole app.
    static_dir = os.path.join(current_app.root_path, "static")
    response = send_from_directory(static_dir, "sw.js")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Service-Worker-Allowed"] = "/"
    return response

@bp.route("/manifest.json")
def web_manifest():
    static_dir = os.path.join(current_app.root_path, "static")
    response = send_from_directory(static_dir, "manifest.json")
    response.headers["Cache-Control"] = "no-cache"
    return response

@bp.route("/.well-known/assetlinks.json")
def assetlinks():
    static_dir = os.path.join(
        current_app.root_path,
        "static",
        ".well-known"
    )
    response = send_from_directory(
        static_dir,
        "assetlinks.json",
        mimetype="application/json"
    )
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response


# ── Analyse ───────────────────────────────────────────────
@bp.route("/analyse", methods=["POST"])
def analyse():
    # 1. File presence
    if "resume" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["resume"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # 2. Extension check
    original_name = secure_filename(file.filename or "")
    if not original_name or not _allowed_file(original_name):
        return jsonify({"error": "Only PDF files are accepted"}), 400

    # 3. JD size cap
    max_jd = current_app.config.get("MAX_JD_CHARS", 20_000)
    jd_raw = request.form.get("job_description", "")
    jd_text = jd_raw[:max_jd].strip()

    # 4. Unique temp path — prevents concurrent upload collision
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    tmp_name = f"{uuid.uuid4().hex}_{original_name}"
    filepath = os.path.join(upload_folder, tmp_name)

    try:
        file.save(filepath)

        # 5. Validate it is actually a PDF (magic bytes)
        with open(filepath, "rb") as f:
            header = f.read(5)
        if header != b"%PDF-":
            return jsonify({"error": "Uploaded file is not a valid PDF"}), 400

        # 6. Extract
        pages = extract_text_by_page(filepath)
        full_text = "\n".join(pages)

        if not full_text.strip():
            return jsonify({
                "error": "No text could be extracted. "
                         "This PDF may be scanned or image-only."
            }), 422

        resume_info = extract_resume_info(full_text)
        resume_skills = extract_skills(full_text)

        # 7. Match
        matched, missing, jd_skills = match_skills(resume_skills, jd_text)
        scores = compute_match_score(full_text, jd_text, matched, missing)

        # 8. Warnings (non-fatal)
        warnings = []
        if jd_text and len(jd_text.split()) < 10:
            warnings.append(
                "Job description seems very short — results may be less accurate."
            )
        if not resume_skills:
            warnings.append("No skills detected in this resume.")

        result = {
            "scores": scores,
            "resume_info": resume_info,
            "skills": {
                "resume_skills": resume_skills,
                "matched_skills": matched,
                "missing_skills": missing,
                "jd_skills": jd_skills,
            },
            "pages": pages,
            "page_count": len(pages),
            "word_count": len(full_text.split()),
            "filename": original_name,
            "warnings": warnings,
        }

        # 9. Persist — _safe_float guards None scores (no-JD case)
        db_id = db.save_analysis(
            filename=original_name,
            jd_summary=jd_text[:300],
            overall_score=_safe_float(scores.get("overall")),
            text_similarity=_safe_float(scores.get("text_similarity")),
            skill_match=_safe_float(scores.get("skill_match")),
            matched_skills=matched,
            missing_skills=missing,
            resume_name=resume_info.get("name", ""),
        )
        result["db_id"] = db_id

        return jsonify(result)

    except Exception as exc:
        # Log detail server-side; return generic message to client
        log.exception("Analysis error for file %r: %s", original_name, exc)
        return jsonify({"error": "Analysis failed. Check your PDF and try again."}), 500

    finally:
        # Always clean up temp file
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except OSError as exc:
            log.warning("Could not remove temp file %r: %s", filepath, exc)


# ── History list ──────────────────────────────────────────
@bp.route("/history")
def history():
    records = db.get_all_history()
    return render_template("history.html", records=records)


# ── History detail ────────────────────────────────────────
@bp.route("/history/<int:record_id>")
def history_detail(record_id):
    record = db.get_analysis(record_id)
    if record is None:
        flash("Record not found or already deleted.", "error")
        return redirect(url_for("main.history"))
    return render_template("history_detail.html", record=record)


# ── Delete one record ─────────────────────────────────────
@bp.route("/history/<int:record_id>/delete", methods=["POST"])
def delete_record(record_id):
    ok = db.delete_analysis(record_id)
    if ok:
        flash("Record deleted.", "success")
    else:
        flash("Could not delete record.", "error")
    return redirect(url_for("main.history"))


# ── Clear all history ─────────────────────────────────────
@bp.route("/history/clear", methods=["POST"])
def clear_history():
    confirmed = request.form.get("confirm", "").strip().lower()
    if confirmed != "yes":
        flash("Clear cancelled — confirmation required.", "warning")
        return redirect(url_for("main.history"))
    ok = db.clear_all_history()
    if ok:
        flash("All history cleared.", "success")
    else:
        flash("Could not clear history.", "error")
    return redirect(url_for("main.history"))


# ── 413 handler — file too large ──────────────────────────
@bp.app_errorhandler(413)
def too_large(_e):
    mb = current_app.config.get("MAX_CONTENT_LENGTH", 0) // (1024 * 1024)
    return jsonify({"error": f"File too large. Maximum size is {mb} MB."}), 413
