from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, redirect, request, url_for

from .config import Config
from .extensions import db, migrate


def create_app(config_object: type[Config] = Config) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["DATA_ROOT"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["KNOWLEDGE_ROOT"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["TEMPLATE_ROOT"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["LOG_ROOT"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["BACKUP_ROOT"]).mkdir(parents=True, exist_ok=True)

    from .services.logging_config import configure_logging
    configure_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)

    from . import models  # noqa: F401
    from .routes.auth import bp as auth_bp
    from .routes.main import bp as main_bp
    from .routes.jobs import bp as jobs_bp
    from .routes.knowledge import bp as knowledge_bp
    from .routes.projects import bp as projects_bp
    from .routes.settings import bp as settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(settings_bp)

    from .cli import register_cli
    register_cli(app)

    from .services.auth import capability_for_endpoint, current_identity

    @app.before_request
    def enforce_packbridge_access():
        if not app.config.get("AUTH_ENABLED", False):
            return None
        endpoint = request.endpoint or ""
        if endpoint in {
            "static",
            "auth.login",
            "auth.login_submit",
            "main.health",
            "main.ready",
        }:
            return None

        identity = current_identity()
        if identity is None:
            if request.method in {"GET", "HEAD"}:
                return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
            return jsonify({"error": "Authentication required."}), 401

        capability = capability_for_endpoint(endpoint, request.method)
        if not identity.can(capability):
            if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"error": "Your PackBridge role does not allow this action."}), 403
            return (
                "Your PackBridge role does not allow this action.",
                403,
            )
        return None

    @app.context_processor
    def inject_packbridge_identity():
        identity = current_identity()
        return {
            "packbridge_user": identity,
            "packbridge_auth_enabled": bool(app.config.get("AUTH_ENABLED", False)),
            "packbridge_can": (
                identity.can if identity is not None else (lambda capability: False)
            ),
        }

    if app.config.get("AUTO_CREATE_DB", True):
        with app.app_context():
            db.create_all()

    return app
