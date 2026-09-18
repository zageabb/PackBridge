from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for
from sqlalchemy import select

from packbridge.extensions import db
from packbridge.models import Job, SSDOutputRecord, SSDProject, SSDProjectJob
from packbridge.ssd_schemas import SSDCaseContext, SSDContext, SSDHeaderContext
from packbridge.services.aggregation import AggregationInput, build_project_preview
from packbridge.services.working_data import load_packing
from packbridge.services.ssd_writer import SSDWriterError, write_socs_preview
from packbridge.services.template_store import active_template

bp = Blueprint("projects", __name__, url_prefix="/projects")


def _text(name: str) -> str | None:
    value = str(request.form.get(name) or "").strip()
    return value or None


def _context(project: SSDProject) -> SSDContext:
    if not project.context_json:
        return SSDContext()
    try:
        return SSDContext.model_validate_json(project.context_json)
    except ValueError:
        return SSDContext()


def _mapped_inputs(project: SSDProject) -> list[AggregationInput]:
    inputs = []
    for link in project.job_links:
        if not link.job.working_json:
            continue
        try:
            packing = load_packing(link.job.working_json)
        except ValueError:
            continue
        inputs.append(
            AggregationInput(
                job_id=link.job.id,
                job_title=link.job.title,
                packing=packing,
            )
        )
    return inputs


@bp.get("/")
def index():
    projects = SSDProject.query.order_by(SSDProject.updated_at.desc()).all()
    return render_template("projects/index.html", projects=projects)


@bp.post("/")
def create():
    name = _text("name")
    if not name:
        flash("Project name is required.", "danger")
        return redirect(url_for("projects.index"))
    project = SSDProject(
        name=name[:255],
        reference=(_text("reference") or "")[:120] or None,
        description=_text("description"),
        context_json=SSDContext().model_dump_json(),
    )
    db.session.add(project)
    db.session.commit()
    flash("SSD project created.", "success")
    return redirect(url_for("projects.view", project_id=project.id))


@bp.get("/<int:project_id>")
def view(project_id: int):
    project = SSDProject.query.get_or_404(project_id)
    context = _context(project)
    inputs = _mapped_inputs(project)
    preview = build_project_preview(inputs, context)
    template = active_template(current_app.config["TEMPLATE_ROOT"])
    generation_ready = bool(
        preview.rows
        and not preview.blocking
        and not preview.warnings
        and template
        and template.get("available")
        and (template.get("inspection") or {}).get("generation_ready")
        and (template.get("inspection") or {}).get("has_vba")
    )

    attached_job_ids = {link.job_id for link in project.job_links}
    linked_elsewhere = {
        row[0]
        for row in db.session.execute(
            select(SSDProjectJob.job_id).where(SSDProjectJob.project_id != project.id)
        ).all()
    }
    available_jobs = (
        Job.query.filter(Job.working_json.isnot(None))
        .order_by(Job.created_at.desc())
        .all()
    )
    available_jobs = [
        job
        for job in available_jobs
        if job.id not in attached_job_ids and job.id not in linked_elsewhere
    ]

    return render_template(
        "projects/detail.html",
        project=project,
        context=context,
        preview=preview,
        available_jobs=available_jobs,
        total_packages=len(preview.rows),
        template=template,
        generation_ready=generation_ready,
    )


@bp.post("/<int:project_id>/jobs")
def attach_job(project_id: int):
    project = SSDProject.query.get_or_404(project_id)
    try:
        job_id = int(request.form.get("job_id") or 0)
    except ValueError:
        job_id = 0
    job = Job.query.get(job_id)
    if not job or not job.working_json:
        flash("Choose a mapped packing-list job.", "danger")
        return redirect(url_for("projects.view", project_id=project.id))

    existing = SSDProjectJob.query.filter_by(job_id=job.id).first()
    if existing:
        flash("That job is already attached to an SSD project.", "warning")
        return redirect(url_for("projects.view", project_id=project.id))

    ordinal = max((link.ordinal for link in project.job_links), default=-1) + 1
    db.session.add(
        SSDProjectJob(
            project_id=project.id,
            job_id=job.id,
            ordinal=ordinal,
        )
    )
    db.session.commit()
    flash(f"Added {job.title} to {project.name}.", "success")
    return redirect(url_for("projects.view", project_id=project.id))


@bp.post("/<int:project_id>/jobs/<int:job_id>/remove")
def detach_job(project_id: int, job_id: int):
    project = SSDProject.query.get_or_404(project_id)
    link = SSDProjectJob.query.filter_by(project_id=project.id, job_id=job_id).first()
    if link:
        db.session.delete(link)
        db.session.commit()
        flash("Packing-list job removed from the SSD project.", "success")
    return redirect(url_for("projects.view", project_id=project.id))


@bp.post("/<int:project_id>/context")
def update_context(project_id: int):
    project = SSDProject.query.get_or_404(project_id)
    current = _context(project)

    header = SSDHeaderContext(
        currency=_text("header_currency"),
        supplier_name=_text("header_supplier_name"),
        pickup_address=_text("header_pickup_address"),
        supplier_contact=_text("header_supplier_contact"),
        supplier_phone_email=_text("header_supplier_phone_email"),
        preliminary_final=_text("header_preliminary_final"),
        bu_details=_text("header_bu_details"),
        project_name=_text("header_project_name"),
        delivery_location=_text("header_delivery_location"),
        contact_person_number=_text("header_contact_person_number"),
        other_remarks=_text("header_other_remarks"),
        supplier_reference=_text("header_supplier_reference"),
    )

    border_text = _text("default_border_crossing_value")
    border_value = None
    if border_text is not None:
        try:
            border_value = float(border_text.replace(",", ""))
        except ValueError:
            flash("Border Crossing Value must be numeric.", "danger")
            return redirect(url_for("projects.view", project_id=project.id) + "#project-preview")

    defaults = SSDCaseContext(
        content_description=_text("default_content_description"),
        equipment_group=_text("default_equipment_group"),
        border_crossing_value=border_value,
        declare_as=_text("default_declare_as"),
        purchase_order=_text("default_purchase_order"),
        purchase_order_position=_text("default_purchase_order_position"),
        pickup_week_planned=_text("default_pickup_week_planned"),
        pickup_week_actual=_text("default_pickup_week_actual"),
        storage_requirement=_text("default_storage_requirement"),
        packaging_material=_text("default_packaging_material"),
        stackability=_text("default_stackability"),
        dangerous_goods=_text("default_dangerous_goods"),
        item_designation=_text("default_item_designation"),
        remarks=_text("default_remarks"),
    )

    project.context_json = SSDContext(
        header=header,
        defaults=defaults,
        case_overrides=current.case_overrides,
    ).model_dump_json()
    db.session.commit()
    flash("SSD project context saved.", "success")
    return redirect(url_for("projects.view", project_id=project.id) + "#project-preview")



@bp.post("/<int:project_id>/build-validation")
def build_validation_workbook(project_id: int):
    project = SSDProject.query.get_or_404(project_id)
    context = _context(project)
    preview = build_project_preview(_mapped_inputs(project), context)
    template = active_template(current_app.config["TEMPLATE_ROOT"])

    if not preview.rows:
        flash("Attach at least one mapped packing-list job before building a workbook.", "danger")
        return redirect(url_for("projects.view", project_id=project.id) + "#outputs")
    if preview.blocking:
        flash("Resolve blocking SSD preview issues before building a workbook.", "danger")
        return redirect(url_for("projects.view", project_id=project.id) + "#project-preview")
    if preview.warnings:
        flash("Resolve SSD preview warnings/missing context before building a validation workbook.", "warning")
        return redirect(url_for("projects.view", project_id=project.id) + "#project-preview")
    if not template or not template.get("available"):
        flash("Install a controlled SSD template first.", "danger")
        return redirect(url_for("settings.index"))
    inspection = template.get("inspection") or {}
    if not inspection.get("generation_ready"):
        flash("The active SSD template is not a clean generation template.", "danger")
        return redirect(url_for("settings.index"))
    if not inspection.get("has_vba"):
        flash("The first controlled validation writer requires the macro-enabled template.", "danger")
        return redirect(url_for("settings.index"))

    output_root = (
        Path(current_app.config["DATA_ROOT"])
        / "ssd-projects"
        / str(project.id)
        / "output"
    )
    output_root.mkdir(parents=True, exist_ok=True)
    safe_reference = "".join(
        character if character.isalnum() or character in "-_" else "-"
        for character in (project.reference or project.name)
    ).strip("-_") or f"project-{project.id}"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    suffix = Path(template["path"]).suffix.casefold() or ".xlsm"
    filename = f"PackBridge-{safe_reference}-VALIDATION-{timestamp}{suffix}"
    destination = output_root / filename

    try:
        result = write_socs_preview(
            template["path"],
            destination,
            preview,
            require_vba=True,
        )
    except (SSDWriterError, OSError, ValueError) as exc:
        flash(f"SSD validation workbook was not created: {exc}", "danger")
        return redirect(url_for("projects.view", project_id=project.id) + "#outputs")

    record = SSDOutputRecord(
        project_id=project.id,
        output_type="validation",
        filename=filename,
        path=str(destination),
        sha256=result["sha256"],
        template_sha256=str(template.get("sha256") or ""),
        structural_fingerprint=result["structural_fingerprint"],
        rows_written=result["rows_written"],
        cells_written=result["cells_written"],
        status="verified",
    )
    db.session.add(record)
    db.session.commit()
    flash(
        "Validation SSD workbook created and re-verified. It is not yet SAP-approved.",
        "success",
    )
    return redirect(url_for("projects.view", project_id=project.id) + "#outputs")


@bp.get("/<int:project_id>/outputs/<int:output_id>/download")
def download_output(project_id: int, output_id: int):
    project = SSDProject.query.get_or_404(project_id)
    record = SSDOutputRecord.query.filter_by(
        id=output_id,
        project_id=project.id,
    ).first_or_404()

    path = Path(record.path).resolve()
    data_root = Path(current_app.config["DATA_ROOT"]).resolve()
    if data_root != path and data_root not in path.parents:
        abort(403)
    if not path.is_file():
        abort(404)

    return send_file(
        path,
        as_attachment=True,
        download_name=record.filename,
        mimetype="application/vnd.ms-excel.sheet.macroEnabled.12",
    )
