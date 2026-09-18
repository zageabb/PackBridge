from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from packbridge.services import runtime_settings
from packbridge.services.template_store import (
    TemplateInstallError,
    active_template,
    clean_active_template,
    install_template,
)

bp = Blueprint("settings", __name__, url_prefix="/settings")


@bp.get("/")
def index():
    values = runtime_settings.current()
    connection = runtime_settings.test_connection()
    template = active_template(current_app.config["TEMPLATE_ROOT"])
    return render_template(
        "settings.html",
        values=values,
        connection=connection,
        template=template,
    )


@bp.post("/")
def update():
    try:
        values = runtime_settings.save(
            {
                "ollama_url": request.form.get("ollama_url", ""),
                "ollama_model": request.form.get("ollama_model", ""),
            }
        )
        connection = runtime_settings.test_connection(
            values["ollama_url"], values["ollama_model"]
        )
        if connection["connected"]:
            flash("Ollama settings saved.", "success")
        else:
            flash("Settings saved, but Ollama could not be reached.", "warning")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("settings.index"))


@bp.post("/test")
def test():
    try:
        connection = runtime_settings.test_connection(
            request.form.get("ollama_url", ""),
            request.form.get("ollama_model", ""),
        )
        if connection["connected"]:
            flash(
                f"Ollama connected. {len(connection['models'])} model(s) available.",
                "success",
            )
        else:
            flash(connection.get("error") or "Ollama connection failed.", "danger")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("settings.index"))


@bp.post("/template")
def template_upload():
    upload = request.files.get("ssd_template")
    if not upload or not upload.filename:
        flash("Choose an XLSM or XLSX SSD template.", "warning")
        return redirect(url_for("settings.index"))
    try:
        template = install_template(current_app.config["TEMPLATE_ROOT"], upload)
        inspection = template["inspection"]
        macro_note = "with VBA" if inspection["has_vba"] else "without VBA"
        flash(
            f"SSD template installed and structurally verified ({macro_note}).",
            "success",
        )
    except (TemplateInstallError, OSError, ValueError) as exc:
        flash(f"SSD template rejected: {exc}", "danger")
    return redirect(url_for("settings.index"))


@bp.post("/template/clean")
def template_clean():
    try:
        template = clean_active_template(current_app.config["TEMPLATE_ROOT"])
        inspection = template["inspection"]
        if not inspection.get("generation_ready"):
            raise TemplateInstallError("Cleaned template did not become generation-ready.")
        flash(
            "Created and activated a clean generation template while preserving the workbook structure and VBA.",
            "success",
        )
    except (TemplateInstallError, OSError, ValueError) as exc:
        flash(f"Could not create clean SSD template: {exc}", "danger")
    return redirect(url_for("settings.index"))
