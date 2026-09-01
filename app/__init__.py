"""
app/__init__.py — Application factory for ResumeLens Stage 9.
"""

import os
import secrets
import logging
from flask import Flask
from . import database as db


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=False)

    is_production = os.environ.get("FLASK_ENV", "production").lower() == "production"
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    # ── core config ──────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    app.config["MAX_CONTENT_LENGTH"] = int(
        os.environ.get("MAX_UPLOAD_BYTES", 10 * 1024 * 1024)  # 10 MB default
    )
    app.config["UPLOAD_FOLDER"] = os.environ.get(
        "UPLOAD_FOLDER",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "instance", "uploads"),
    )
    app.config["ALLOWED_EXTENSIONS"] = {"pdf"}
    app.config["MAX_JD_CHARS"] = 20_000
    app.config["DEBUG"] = debug

    # Secure cookies when actually deployed over HTTPS in production
    if is_production and not debug:
        app.config["SESSION_COOKIE_SECURE"] = True
        app.config["SESSION_COOKIE_HTTPONLY"] = True
        app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # Trust one hop of X-Forwarded-* headers from the platform's reverse
    # proxy (Render / Railway / Fly / nginx) so url_for(_external=True),
    # request.is_secure and client IPs are correct behind HTTPS termination.
    if os.environ.get("TRUST_PROXY", "true").lower() == "true":
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

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
