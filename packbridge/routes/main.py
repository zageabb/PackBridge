from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template

from packbridge.models import Job
from packbridge.services.local_ocr import tesseract_available
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
            "ocr": {
                "mode": current_app.config.get("OCR_MODE", "off"),
                "tesseract_available": tesseract_available(),
            },
            "auth_enabled": bool(current_app.config.get("AUTH_ENABLED", False)),
            "sap_release": {
                "output_approved": bool(current_app.config.get("SAP_OUTPUT_APPROVED", False)),
                "socs_only_approved": bool(current_app.config.get("SAP_SOCS_ONLY_APPROVED", False)),
                "macro_free_approved": bool(current_app.config.get("SAP_MACRO_FREE_APPROVED", False)),
            },
        }
    ), 200 if ollama["connected"] else 503
