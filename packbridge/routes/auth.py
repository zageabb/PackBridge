from __future__ import annotations

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from packbridge.services.auth import (
    AuthConfigurationError,
    authenticate,
    current_identity,
    login_identity,
    logout_identity,
)

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.get("/login")
def login():
    if not current_app.config.get("AUTH_ENABLED", False):
        return redirect(url_for("main.index"))
    if current_identity() is not None:
        return redirect(url_for("main.index"))
    return render_template("login.html")


@bp.post("/login")
def login_submit():
    if not current_app.config.get("AUTH_ENABLED", False):
        return redirect(url_for("main.index"))

    username = str(request.form.get("username") or "").strip()
    password = str(request.form.get("password") or "")
    try:
        identity = authenticate(username, password)
    except AuthConfigurationError as exc:
        flash(str(exc), "danger")
        return render_template("login.html"), 503

    if identity is None:
        flash("Invalid username or password.", "danger")
        return render_template("login.html"), 401

    session.clear()
    login_identity(identity)
    destination = str(request.args.get("next") or "").strip()
    if not destination.startswith("/"):
        destination = url_for("main.index")
    return redirect(destination)


@bp.post("/logout")
def logout():
    logout_identity()
    return redirect(url_for("auth.login"))
