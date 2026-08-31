"""
app/__init__.py — Application factory for ResumeLens Stage 9.
"""

import os
import secrets
from flask import Flask
from . import database as db


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=False)

    # ── core config ──────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    app.config["MAX_CONTENT_LENGTH"] = int(
        os.environ.get("MAX_UPLOAD_BYTES", 10 * 1024 * 1024)  # 10 MB default
    )
    app.config["UPLOAD_FOLDER"] = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "instance", "uploads"
    )
    app.config["ALLOWED_EXTENSIONS"] = {"pdf"}
    app.config["MAX_JD_CHARS"] = 20_000

    # Allow test overrides
    if config:
        app.config.update(config)

    # ── Jinja helpers ────────────────────────────────────────
    @app.template_filter("verdict_class")
    def verdict_class(score):
        """Map a numeric score to a CSS class name."""
        try:
            s = float(score)
        except (TypeError, ValueError):
            return "neutral"
        if s >= 70:
            return "good"
        if s >= 45:
            return "ok"
        return "poor"

    # ── database ─────────────────────────────────────────────
    try:
        db.init_db()
    except Exception as exc:  # pragma: no cover
        app.logger.warning("DB init warning: %s", exc)

    # ── blueprints ───────────────────────────────────────────
    from .routes import bp
    app.register_blueprint(bp)

    return app
