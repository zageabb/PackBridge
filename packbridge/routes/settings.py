from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from packbridge.services import runtime_settings

bp = Blueprint("settings", __name__, url_prefix="/settings")


@bp.get("/")
def index():
    values = runtime_settings.current()
    connection = runtime_settings.test_connection()
    return render_template("settings.html", values=values, connection=connection)


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
