from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template

from packbridge.models import Job
from packbridge.services.runtime_settings import test_connection

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    jobs = Job.query.order_by(Job.created_at.desc()).limit(20).all()
    return render_template("workspace.html", jobs=jobs)


@bp.get("/health")
def health():
    return jsonify({"status": "ok", "app": "PackBridge"})


@bp.get("/ready")
def ready():
    ollama = test_connection()
    return jsonify(
        {
            "status": "ready" if ollama["connected"] else "degraded",
            "database": "ok",
            "ollama": ollama,
            "knowledge_root": str(current_app.config["KNOWLEDGE_ROOT"]),
        }
    ), 200 if ollama["connected"] else 503
