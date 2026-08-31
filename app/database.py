"""
database.py — SQLite persistence for ResumeLens Stage 9.
Uses only Python built-in sqlite3. No ORM required.
Handles None scores (no-JD analyses) safely.
"""

import sqlite3
import json
import os
from datetime import datetime, timezone

_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "instance", "resumelens.db"
)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS analysis_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    filename        TEXT    NOT NULL,
    jd_summary      TEXT,
    overall_score   REAL,
    text_similarity REAL,
    skill_match     REAL,
    matched_skills  TEXT,
    missing_skills  TEXT,
    resume_name     TEXT,
    analysis_date   TEXT    NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(_CREATE_TABLE)
        conn.commit()


def _safe_round(value, ndigits: int = 2):
    """Round float; return None if value is None/non-numeric."""
    if value is None:
        return None
    try:
        return round(float(value), ndigits)
    except (TypeError, ValueError):
        return None


def save_analysis(
    filename: str,
    jd_summary: str,
    overall_score,
    text_similarity,
    skill_match,
    matched_skills: list,
    missing_skills: list,
    resume_name: str,
) -> int | None:
    """Insert one analysis record. Returns new row id, or None on failure."""
    try:
        with _connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO analysis_history
                    (filename, jd_summary, overall_score, text_similarity,
                     skill_match, matched_skills, missing_skills,
                     resume_name, analysis_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    filename,
                    (jd_summary or "")[:300],
                    _safe_round(overall_score),
                    _safe_round(text_similarity),
                    _safe_round(skill_match),
                    json.dumps(matched_skills or []),
                    json.dumps(missing_skills or []),
                    resume_name or "",
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error:
        return None


def get_all_history() -> list[dict]:
    try:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT * FROM analysis_history ORDER BY id DESC"
            ).fetchall()
            return [_row_to_dict(r) for r in rows]
    except sqlite3.Error:
        return []


def get_analysis(record_id: int) -> dict | None:
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT * FROM analysis_history WHERE id = ?", (record_id,)
            ).fetchone()
            return _row_to_dict(row) if row else None
    except sqlite3.Error:
        return None


def delete_analysis(record_id: int) -> bool:
    try:
        with _connect() as conn:
            conn.execute("DELETE FROM analysis_history WHERE id = ?", (record_id,))
            conn.commit()
            return True
    except sqlite3.Error:
        return False


def clear_all_history() -> bool:
    try:
        with _connect() as conn:
            conn.execute("DELETE FROM analysis_history")
            conn.commit()
            return True
    except sqlite3.Error:
        return False


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    for field in ("matched_skills", "missing_skills"):
        try:
            d[field] = json.loads(d.get(field) or "[]")
        except (json.JSONDecodeError, TypeError):
            d[field] = []
    return d
