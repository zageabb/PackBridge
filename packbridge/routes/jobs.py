from __future__ import annotations

import json
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from packbridge.extensions import db
from packbridge.models import AuditEvent, ChatMessage, Job, SSDContextRecord, SourceChunk, SourceDocument
from packbridge.services.document_ingestion import (
    ALLOWED_EXTENSIONS,
    DocumentIngestionError,
    extract_path,
)
from packbridge.services.mapper import MappingError, map_packing_list
from packbridge.services.prompt_service import load_prompt
from packbridge.services.profile_matching import match_profile
from packbridge.services.runtime_settings import client as ollama_client
from packbridge.services.storage import save_job_upload
from packbridge.services.ssd_preview import build_ssd_preview
from packbridge.ssd_schemas import SSDCaseContext, SSDContext
from packbridge.services.working_data import (
    WorkingDataError,
    dump_packing,
    has_modifications,
    issue_counts,
    load_packing,
    revert_all,
    revert_field,
    revert_package,
    set_field,
)

bp = Blueprint("jobs", __name__, url_prefix="/jobs")


def _audit(
    job_id: int,
    event_type: str,
    summary: str,
    payload: dict | None = None,
    actor: str = "system",
) -> None:
    db.session.add(
        AuditEvent(
            job_id=job_id,
            event_type=event_type,
            summary=summary,
            payload_json=json.dumps(payload, default=str) if payload else None,
            actor=actor,
        )
    )


def _working(job: Job) -> dict | None:
    if not job.working_json:
        return None
    try:
        return json.loads(job.working_json)
    except json.JSONDecodeError:
        return None


def _save_working(job: Job, packing) -> None:
    job.working_json = dump_packing(packing)
    job.status = "edited" if has_modifications(packing) else "mapped"
    sales_order = packing.order.sales_order.working.value if packing.order.sales_order.working else None
    job.sales_order = str(sales_order) if sales_order not in (None, "") else None


def _selected_package(packages: list[dict], selected_case: str | None):
    if not packages:
        return None, None
    for index, package in enumerate(packages):
        value = ((package.get("case_number") or {}).get("working") or {}).get("value")
        if selected_case is not None and str(value) == selected_case:
            return package, index
    return packages[0], 0


def _ssd_context(job: Job) -> SSDContext:
    record = SSDContextRecord.query.filter_by(job_id=job.id).first()
    if not record or not record.context_json:
        return SSDContext()
    try:
        return SSDContext.model_validate_json(record.context_json)
    except ValueError:
        return SSDContext()


def _form_text(name: str) -> str | None:
    value = str(request.form.get(name) or "").strip()
    return value or None


@bp.post("/upload")
def upload():
    upload_file = request.files.get("packing_list")
    if not upload_file or not upload_file.filename:
        flash("Choose a packing list to upload.", "warning")
        return redirect(url_for("main.index"))

    suffix = Path(upload_file.filename).suffix.casefold()
    if suffix not in ALLOWED_EXTENSIONS:
        flash(
            "Unsupported source type. Use PDF, DOCX, XLSX/XLSM, CSV, TXT or Markdown.",
            "danger",
        )
        return redirect(url_for("main.index"))

    job = Job(title=Path(upload_file.filename).stem[:255], status="uploading")
    db.session.add(job)
    db.session.flush()

    try:
        original_name, stored_name, path, digest, size = save_job_upload(
            Path(current_app.config["DATA_ROOT"]),
            job.id,
            upload_file,
        )
        document = SourceDocument(
            job_id=job.id,
            original_name=original_name,
            stored_name=stored_name,
            path=str(path),
            size_bytes=size,
            sha256=digest,
            extraction_status="processing",
        )
        db.session.add(document)
        db.session.flush()
        _audit(
            job.id,
            "source_uploaded",
            f"Uploaded {original_name}",
            {"sha256": digest, "size_bytes": size},
        )

        extracted = extract_path(path)
        document.page_count = extracted.page_count
        document.extraction_status = "complete"
        for chunk in extracted.chunks:
            db.session.add(
                SourceChunk(
                    document_id=document.id,
                    position=chunk.position,
                    locator=chunk.locator,
                    text=chunk.text,
                )
            )
        job.status = "extracted"
        _audit(
            job.id,
            "source_extracted",
            f"Extracted {len(extracted.chunks)} source section(s)",
            {"pages": extracted.page_count, "sections": len(extracted.chunks)},
        )
        db.session.commit()
        flash("Packing list uploaded and extracted. Run the local mapper when ready.", "success")
        return redirect(url_for("jobs.view", job_id=job.id))
    except (DocumentIngestionError, OSError, ValueError) as exc:
        job.status = "failed"
        job.error_message = str(exc)
        _audit(job.id, "source_failed", str(exc))
        db.session.commit()
        flash(str(exc), "danger")
        return redirect(url_for("jobs.view", job_id=job.id))


@bp.get("/<int:job_id>")
def view(job_id: int):
    job = Job.query.get_or_404(job_id)
    packing = _working(job)
    packages = (packing or {}).get("packages", [])
    selected, selected_index = _selected_package(packages, request.args.get("case"))
    counts = {"INFO": 0, "WARNING": 0, "BLOCKING": 0}
    ssd_context = _ssd_context(job)
    ssd_preview = None
    if job.working_json:
        try:
            working_model = load_packing(job.working_json)
            counts = issue_counts(working_model)
            ssd_preview = build_ssd_preview(working_model, ssd_context)
        except (ValueError, TypeError):
            pass
    audit_events = (
        AuditEvent.query.filter_by(job_id=job.id)
        .order_by(AuditEvent.id.desc())
        .limit(30)
        .all()
    )
    return render_template(
        "job.html",
        job=job,
        packing=packing,
        packages=packages,
        selected_package=selected,
        selected_package_index=selected_index,
        issue_counts=counts,
        audit_events=audit_events,
        ssd_context=ssd_context,
        ssd_preview=ssd_preview,
        selected_ssd_override=(
            ssd_context.case_overrides.get(
                str((((selected or {}).get("case_number") or {}).get("working") or {}).get("value") or "")
            )
            if selected
            else None
        ),
    )


@bp.post("/<int:job_id>/process")
def process(job_id: int):
    job = Job.query.get_or_404(job_id)
    if (
        job.source_json
        and job.working_json
        and job.source_json != job.working_json
        and request.form.get("confirm_overwrite") != "1"
    ):
        flash(
            "This job contains working-data changes. Reprocessing is blocked until you explicitly discard them.",
            "warning",
        )
        return redirect(url_for("jobs.view", job_id=job.id))

    chunks = (
        SourceChunk.query.join(SourceDocument)
        .filter(SourceDocument.job_id == job.id)
        .order_by(SourceChunk.position)
        .all()
    )
    if not chunks:
        flash("No extracted source text is available for this job.", "danger")
        return redirect(url_for("jobs.view", job_id=job.id))

    document_text = "\n\n".join(f"[{chunk.locator}]\n{chunk.text}" for chunk in chunks)
    profile_hint = request.form.get("profile_hint", "").strip()
    profile_match = None
    if not profile_hint:
        profile_match = match_profile(Path(current_app.config["KNOWLEDGE_ROOT"]), document_text)
        if profile_match:
            profile_hint = (
                f"Matched document profile: {profile_match.title}. "
                f"Knowledge path: {profile_match.path}. "
                f"Matched indicators: {', '.join(profile_match.matched_indicators)}"
            )
            job.document_profile = profile_match.title
            _audit(
                job.id,
                "profile_matched",
                f"Matched document profile {profile_match.title}",
                {
                    "path": profile_match.path,
                    "score": profile_match.score,
                    "total_indicators": profile_match.total_indicators,
                    "matched_indicators": profile_match.matched_indicators,
                },
            )

    job.status = "processing"
    _audit(
        job.id,
        "mapping_started",
        "Local document mapping started",
        {"profile_hint": profile_hint},
    )
    db.session.commit()

    try:
        packing = map_packing_list(document_text, profile_hint=profile_hint)
        payload = packing.model_dump_json()
        job.source_json = payload
        job.working_json = payload
        job.vendor = packing.document.vendor
        job.document_profile = packing.document.document_profile or (profile_match.title if profile_match else job.document_profile)
        sales_order = packing.order.sales_order.working.value if packing.order.sales_order.working else None
        job.sales_order = str(sales_order) if sales_order not in (None, "") else None
        job.status = "mapped"
        job.error_message = None
        _audit(
            job.id,
            "mapping_completed",
            f"Mapped {len(packing.packages)} package(s)",
            {
                "packages": len(packing.packages),
                "model": ollama_client().model,
                "issues": issue_counts(packing),
            },
        )
        db.session.commit()
        flash(f"Local mapper returned {len(packing.packages)} package(s).", "success")
    except MappingError as exc:
        job.status = "mapping_failed"
        job.error_message = str(exc)
        _audit(job.id, "mapping_failed", str(exc))
        db.session.commit()
        flash(str(exc), "danger")
    return redirect(url_for("jobs.view", job_id=job.id))


@bp.post("/<int:job_id>/field")
def edit_field(job_id: int):
    job = Job.query.get_or_404(job_id)
    if not job.working_json:
        return jsonify({"error": "This job has no mapped working data."}), 409

    payload = request.get_json(silent=True) or {}
    path = str(payload.get("path") or "").strip()
    reason = str(payload.get("reason") or "").strip()
    actor = str(payload.get("actor") or "user").strip()[:120] or "user"

    try:
        packing = load_packing(job.working_json)
        packing, change = set_field(
            packing,
            path,
            payload.get("value"),
            unit=payload.get("unit") if "unit" in payload else None,
            actor=actor,
            reason=reason,
        )
        _save_working(job, packing)
        _audit(
            job.id,
            "working_field_changed",
            f"Updated {path}",
            {**change, "reason": reason or None, "issues": issue_counts(packing)},
            actor=actor,
        )
        db.session.commit()
        return jsonify(
            {
                "ok": True,
                "change": change,
                "issues": [issue.model_dump() for issue in packing.issues],
                "issue_counts": issue_counts(packing),
                "status": job.status,
            }
        )
    except WorkingDataError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.post("/<int:job_id>/field/revert")
def revert_working_field(job_id: int):
    job = Job.query.get_or_404(job_id)
    payload = request.get_json(silent=True) or {}
    path = str(payload.get("path") or "").strip()
    if not job.working_json:
        return jsonify({"error": "This job has no mapped working data."}), 409

    try:
        packing = load_packing(job.working_json)
        packing, change = revert_field(packing, path)
        _save_working(job, packing)
        _audit(
            job.id,
            "working_field_reverted",
            f"Reverted {path} to source",
            {**change, "issues": issue_counts(packing)},
            actor="user",
        )
        db.session.commit()
        return jsonify(
            {
                "ok": True,
                "change": change,
                "issue_counts": issue_counts(packing),
                "status": job.status,
            }
        )
    except WorkingDataError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.post("/<int:job_id>/packages/<int:package_index>/revert")
def revert_working_package(job_id: int, package_index: int):
    job = Job.query.get_or_404(job_id)
    if not job.working_json:
        return jsonify({"error": "This job has no mapped working data."}), 409

    try:
        packing = load_packing(job.working_json)
        case_before = (
            packing.packages[package_index].case_number.working.value
            if package_index < len(packing.packages)
            and packing.packages[package_index].case_number.working
            else None
        )
        packing, changed = revert_package(packing, package_index)
        _save_working(job, packing)
        _audit(
            job.id,
            "working_package_reverted",
            f"Reverted package {case_before or package_index + 1} to source",
            {"package_index": package_index, "changed_fields": changed, "issues": issue_counts(packing)},
            actor="user",
        )
        db.session.commit()
        return jsonify(
            {
                "ok": True,
                "changed_fields": changed,
                "issue_counts": issue_counts(packing),
                "status": job.status,
            }
        )
    except (WorkingDataError, IndexError) as exc:
        return jsonify({"error": str(exc)}), 400


@bp.post("/<int:job_id>/revert-all")
def revert_working_job(job_id: int):
    job = Job.query.get_or_404(job_id)
    if not job.working_json:
        return jsonify({"error": "This job has no mapped working data."}), 409

    packing = load_packing(job.working_json)
    packing, changed = revert_all(packing)
    _save_working(job, packing)
    _audit(
        job.id,
        "working_job_reverted",
        "Reverted all working values to source",
        {"changed_fields": changed, "issues": issue_counts(packing)},
        actor="user",
    )
    db.session.commit()
    return jsonify(
        {
            "ok": True,
            "changed_fields": changed,
            "issue_counts": issue_counts(packing),
            "status": job.status,
        }
    )


@bp.post("/<int:job_id>/ssd-context")
def update_ssd_context(job_id: int):
    job = Job.query.get_or_404(job_id)
    context = _ssd_context(job)

    header_fields = (
        "currency",
        "supplier_name",
        "pickup_address",
        "supplier_contact",
        "preliminary_final",
        "bu_details",
        "project_name",
        "delivery_location",
        "contact_person_number",
        "other_remarks",
        "supplier_reference",
    )
    default_fields = (
        "content_description",
        "equipment_group",
        "declare_as",
        "purchase_order",
        "purchase_order_position",
        "pickup_week_planned",
        "pickup_week_actual",
        "storage_requirement",
        "packaging_material",
        "stackability",
        "dangerous_goods",
        "item_designation",
        "remarks",
    )

    header_values = context.header.model_dump()
    for name in header_fields:
        header_values[name] = _form_text("header_" + name)

    default_values = context.defaults.model_dump()
    for name in default_fields:
        default_values[name] = _form_text("default_" + name)

    border_value = _form_text("default_border_crossing_value")
    if border_value is None:
        default_values["border_crossing_value"] = None
    else:
        try:
            default_values["border_crossing_value"] = float(border_value.replace(",", ""))
        except ValueError:
            flash("Border Crossing Value must be numeric.", "danger")
            return redirect(url_for("jobs.view", job_id=job.id) + "#output-preview")

    updated = SSDContext.model_validate(
        {
            "header": header_values,
            "defaults": default_values,
            "case_overrides": {
                key: value.model_dump()
                for key, value in context.case_overrides.items()
            },
        }
    )

    record = SSDContextRecord.query.filter_by(job_id=job.id).first()
    if record is None:
        record = SSDContextRecord(job_id=job.id)
        db.session.add(record)
    record.context_json = updated.model_dump_json()
    record.updated_by = "user"
    _audit(
        job.id,
        "ssd_context_updated",
        "Updated SSD project/default context",
        {
            "header_fields": [name for name, value in header_values.items() if value not in (None, "")],
            "default_fields": [name for name, value in default_values.items() if value not in (None, "")],
        },
        actor="user",
    )
    db.session.commit()
    flash("SSD project/default context saved.", "success")
    return redirect(url_for("jobs.view", job_id=job.id) + "#output-preview")


@bp.post("/<int:job_id>/ssd-context/case")
def update_ssd_case_context(job_id: int):
    job = Job.query.get_or_404(job_id)
    if not job.working_json:
        flash("Map the packing list before adding a case-specific SSD override.", "warning")
        return redirect(url_for("jobs.view", job_id=job.id) + "#output-preview")

    case_number = _form_text("case_number")
    if not case_number:
        flash("Case number is required for an SSD override.", "danger")
        return redirect(url_for("jobs.view", job_id=job.id) + "#output-preview")

    packing = load_packing(job.working_json)
    available_cases = {
        str(package.case_number.working.value)
        for package in packing.packages
        if package.case_number.working and package.case_number.working.value not in (None, "")
    }
    if case_number not in available_cases:
        flash("The selected case is not present in the current working dataset.", "danger")
        return redirect(url_for("jobs.view", job_id=job.id) + "#output-preview")

    context = _ssd_context(job)
    values = (
        context.case_overrides.get(case_number).model_dump()
        if case_number in context.case_overrides
        else {}
    )

    fields = (
        "content_description",
        "equipment_group",
        "declare_as",
        "purchase_order",
        "purchase_order_position",
        "pickup_week_planned",
        "pickup_week_actual",
        "storage_requirement",
        "packaging_material",
        "stackability",
        "dangerous_goods",
        "item_designation",
        "remarks",
    )
    for name in fields:
        values[name] = _form_text("case_" + name)

    border_value = _form_text("case_border_crossing_value")
    if border_value is None:
        values["border_crossing_value"] = None
    else:
        try:
            values["border_crossing_value"] = float(border_value.replace(",", ""))
        except ValueError:
            flash("Case Border Crossing Value must be numeric.", "danger")
            return redirect(
                url_for("jobs.view", job_id=job.id, case=case_number) + "#output-preview"
            )

    override = SSDCaseContext.model_validate(values)
    if any(value not in (None, "") for value in override.model_dump().values()):
        context.case_overrides[case_number] = override
        action = "updated"
    else:
        context.case_overrides.pop(case_number, None)
        action = "cleared"

    record = SSDContextRecord.query.filter_by(job_id=job.id).first()
    if record is None:
        record = SSDContextRecord(job_id=job.id)
        db.session.add(record)
    record.context_json = context.model_dump_json()
    record.updated_by = "user"
    _audit(
        job.id,
        "ssd_case_context_updated",
        f"SSD case override {action} for {case_number}",
        {
            "case_number": case_number,
            "action": action,
            "fields": [
                name for name, value in override.model_dump().items()
                if value not in (None, "")
            ],
        },
        actor="user",
    )
    db.session.commit()
    flash(f"SSD case override {action} for {case_number}.", "success")
    return redirect(url_for("jobs.view", job_id=job.id, case=case_number) + "#output-preview")


@bp.post("/<int:job_id>/ssd-context/case/reset")
def reset_ssd_case_context(job_id: int):
    job = Job.query.get_or_404(job_id)
    case_number = _form_text("case_number")
    if not case_number:
        flash("Case number is required.", "danger")
        return redirect(url_for("jobs.view", job_id=job.id) + "#output-preview")

    context = _ssd_context(job)
    existed = context.case_overrides.pop(case_number, None) is not None
    record = SSDContextRecord.query.filter_by(job_id=job.id).first()
    if record is None:
        record = SSDContextRecord(job_id=job.id)
        db.session.add(record)
    record.context_json = context.model_dump_json()
    record.updated_by = "user"
    if existed:
        _audit(
            job.id,
            "ssd_case_context_reset",
            f"Reset SSD case override for {case_number}",
            {"case_number": case_number},
            actor="user",
        )
    db.session.commit()
    flash(
        f"SSD case override reset for {case_number}." if existed
        else f"No SSD case override existed for {case_number}.",
        "success",
    )
    return redirect(url_for("jobs.view", job_id=job.id, case=case_number) + "#output-preview")


@bp.post("/<int:job_id>/chat")
def chat(job_id: int):
    job = Job.query.get_or_404(job_id)
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message") or "").strip()
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    if not message:
        return jsonify({"error": "Message is required."}), 400

    user_message = ChatMessage(
        job_id=job.id,
        role="user",
        content=message,
        context_json=json.dumps(context),
    )
    db.session.add(user_message)
    db.session.flush()

    recent = (
        ChatMessage.query.filter_by(job_id=job.id)
        .order_by(ChatMessage.id.desc())
        .limit(20)
        .all()
    )
    history = [{"role": row.role, "content": row.content} for row in reversed(recent)]

    job_context = {
        "job_id": job.id,
        "status": job.status,
        "vendor": job.vendor,
        "document_profile": job.document_profile,
        "sales_order": job.sales_order,
        "selected_context": context,
        "working_data": _working(job),
    }
    system_prompt = (
        load_prompt("job_assistant")
        + "\n\nCURRENT JOB CONTEXT:\n"
        + json.dumps(job_context, default=str)[:60_000]
    )
    result = ollama_client().chat(history, system_prompt=system_prompt)

    if result.available:
        answer = str(result.value)
    else:
        answer = f"Local assistant unavailable: {result.warning or result.error_code}"

    db.session.add(
        ChatMessage(
            job_id=job.id,
            role="assistant",
            content=answer,
            context_json=json.dumps(context),
        )
    )
    _audit(
        job.id,
        "assistant_message",
        "Assistant responded to job question",
        {"context": context},
    )
    db.session.commit()
    return jsonify({"message": answer})


@bp.get("/<int:job_id>/chat/history")
def chat_history(job_id: int):
    Job.query.get_or_404(job_id)
    messages = ChatMessage.query.filter_by(job_id=job_id).order_by(ChatMessage.id).all()
    return jsonify(
        {
            "messages": [
                {
                    "role": row.role,
                    "content": row.content,
                    "created_at": row.created_at.isoformat(),
                }
                for row in messages
            ]
        }
    )
