from __future__ import annotations

from pathlib import Path

from flask import Flask

from .config import Config
from .extensions import db, migrate


def create_app(config_object: type[Config] = Config) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["DATA_ROOT"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["KNOWLEDGE_ROOT"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["TEMPLATE_ROOT"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)

    from . import models  # noqa: F401
    from .routes.main import bp as main_bp
    from .routes.jobs import bp as jobs_bp
    from .routes.knowledge import bp as knowledge_bp
    from .routes.projects import bp as projects_bp
    from .routes.settings import bp as settings_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(settings_bp)

    if app.config.get("AUTO_CREATE_DB", True):
        with app.app_context():
            db.create_all()

    return app
