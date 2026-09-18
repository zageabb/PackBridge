from __future__ import annotations

from datetime import datetime, timezone
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

from packbridge.assistant_schemas import AssistantStructuredReply
from packbridge.extensions import db
from packbridge.models import (
    AssistantProposalRecord,
    AuditEvent,
    ChatMessage,
    Job,
    SSDContextRecord,
    SourceChunk,
    SourceDocument,
    ValidationAcknowledgement,
)
from packbridge.services.assistant_context import build_assistant_context
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
from packbridge.services.validation_acknowledgements import (
    acknowledge_issue,
    active_acknowledgements,
    apply_acknowledgements,
    issue_fingerprint,
    revoke_acknowledgement,
)
from packbridge.services.source_evidence import find_source_evidence
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
    counts = {"INFO": 0, "WARNING": 0, "BLOCKING": 0}
    resolved_warning_count = 0
    ssd_context = _ssd_context(job)
    ssd_preview = None

    if job.working_json:
        try:
            working_model = load_packing(job.working_json)
            acknowledgements = active_acknowledgements(job.id)
            apply_acknowledgements(working_model, acknowledgements)
            counts = issue_counts(working_model)
            resolved_warning_count = sum(
                1 for issue in working_model.issues if issue.severity == "WARNING" and issue.resolved
            )
            ssd_preview = build_ssd_preview(working_model, ssd_context)
            packing = working_model.model_dump(mode="json")
            for issue_dict, issue_model in zip(packing.get("issues", []), working_model.issues):
                issue_dict["fingerprint"] = issue_fingerprint(issue_model)
        except (ValueError, TypeError):
            pass

    packages = (packing or {}).get("packages", [])
    selected, selected_index = _selected_package(packages, request.args.get("case"))

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
        resolved_warning_count=resolved_warning_count,
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


@bp.post("/<int:job_id>/issues/acknowledge")
def acknowledge_validation_issue(job_id: int):
    job = Job.query.get_or_404(job_id)
    if not job.working_json:
        return jsonify({"error": "This job has no mapped working data."}), 409

    payload = request.get_json(silent=True) or {}
    fingerprint = str(payload.get("fingerprint") or "").strip()
    reason = str(payload.get("reason") or "").strip()
    actor = str(payload.get("actor") or "user").strip()[:120] or "user"

    packing = load_packing(job.working_json)
    current = next(
        (issue for issue in packing.issues if issue_fingerprint(issue) == fingerprint),
        None,
    )
    if current is None:
        return jsonify({"error": "This validation issue is no longer current."}), 409
    if current.severity != "WARNING":
        return jsonify({"error": "Only warnings can be acknowledged. Blocking issues must be resolved."}), 400

    try:
        row = acknowledge_issue(job.id, current, reason=reason, actor=actor)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    db.session.add(row)
    _audit(
        job.id,
        "validation_warning_acknowledged",
        f"Acknowledged {current.code}",
        {
            "fingerprint": fingerprint,
            "code": current.code,
            "case_number": current.case_number,
            "field_path": current.field_path,
            "message": current.message,
            "reason": reason or None,
        },
        actor=actor,
    )
    db.session.commit()

    apply_acknowledgements(packing, active_acknowledgements(job.id))
    return jsonify(
        {
            "ok": True,
            "fingerprint": fingerprint,
            "issue_counts": issue_counts(packing),
            "resolved_warning_count": sum(
                1 for issue in packing.issues if issue.severity == "WARNING" and issue.resolved
            ),
        }
    )


@bp.post("/<int:job_id>/issues/reopen")
def reopen_validation_issue(job_id: int):
    job = Job.query.get_or_404(job_id)
    payload = request.get_json(silent=True) or {}
    fingerprint = str(payload.get("fingerprint") or "").strip()
    actor = str(payload.get("actor") or "user").strip()[:120] or "user"

    row = ValidationAcknowledgement.query.filter_by(
        job_id=job.id,
        issue_fingerprint=fingerprint,
        status="active",
    ).first()
    if row is None:
        return jsonify({"error": "No active acknowledgement exists for this warning."}), 404

    revoke_acknowledgement(row, actor=actor)
    _audit(
        job.id,
        "validation_warning_reopened",
        f"Reopened {row.issue_code}",
        {
            "fingerprint": fingerprint,
            "code": row.issue_code,
            "case_number": row.case_number,
            "field_path": row.field_path,
        },
        actor=actor,
    )
    db.session.commit()
    return jsonify({"ok": True, "fingerprint": fingerprint})


@bp.post("/<int:job_id>/ssd-context")
def update_ssd_context(job_id: int):
    job = Job.query.get_or_404(job_id)
    context = _ssd_context(job)

    header_fields = (
        "currency",
        "supplier_name",
        "pickup_address",
        "supplier_contact",
        "supplier_phone_email",
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


def _proposal_dict(record: AssistantProposalRecord | None) -> dict | None:
    if record is None:
        return None
    try:
        changes = json.loads(record.changes_json)
    except json.JSONDecodeError:
        changes = []
    return {
        "id": record.id,
        "status": record.status,
        "changes": changes,
        "created_at": record.created_at.isoformat(),
        "decided_at": record.decided_at.isoformat() if record.decided_at else None,
        "decided_by": record.decided_by,
    }


def _validate_assistant_changes(job: Job, proposed_changes) -> list[dict]:
    if not job.working_json:
        return []

    packing = load_packing(job.working_json)
    validated = []
    seen_paths: set[str] = set()

    for proposed in proposed_changes:
        path = str(proposed.path or "").strip()
        if (
            not path
            or path in seen_paths
            or ".source" in path
            or ".working" in path
            or path.startswith("_")
        ):
            continue
        try:
            packing, change = set_field(
                packing,
                path,
                proposed.value,
                unit=proposed.unit,
                actor="assistant-proposal",
                reason=proposed.reason,
            )
        except (WorkingDataError, ValueError, TypeError):
            continue
        seen_paths.add(path)
        validated.append(
            {
                "path": path,
                "value": change["after"]["value"],
                "unit": change["after"]["unit"],
                "reason": proposed.reason,
                "before": change["before"],
            }
        )
    return validated


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

    packing_model = None
    if job.working_json:
        try:
            packing_model = load_packing(job.working_json)
            apply_acknowledgements(
                packing_model,
                active_acknowledgements(job.id),
            )
        except ValueError:
            packing_model = None

    selected_case = str(context.get("selected_case") or "").strip() or None
    job_context = build_assistant_context(job, packing_model, selected_case)
    job_context["selected_context"] = context
    system_prompt = (
        load_prompt("job_assistant")
        + "\n\nCURRENT GROUNDED JOB CONTEXT:\n"
        + json.dumps(job_context, default=str)[:32_000]
    )

    client = ollama_client()
    structured = client.chat_json(
        history,
        AssistantStructuredReply,
        system_prompt=system_prompt,
    )

    proposal_changes = []
    if structured.available:
        reply = structured.value
        answer = reply.message
        if reply.clarification_question:
            answer += "\n\n" + reply.clarification_question
        proposal_changes = _validate_assistant_changes(job, reply.proposed_changes)
    else:
        fallback = client.chat(history, system_prompt=system_prompt)
        answer = (
            str(fallback.value)
            if fallback.available
            else f"Local assistant unavailable: {fallback.warning or structured.warning or fallback.error_code or structured.error_code}"
        )

    assistant_message = ChatMessage(
        job_id=job.id,
        role="assistant",
        content=answer,
        context_json=json.dumps(context),
    )
    db.session.add(assistant_message)
    db.session.flush()

    proposal = None
    if proposal_changes:
        proposal = AssistantProposalRecord(
            job_id=job.id,
            assistant_message_id=assistant_message.id,
            status="pending",
            changes_json=json.dumps(proposal_changes, default=str),
        )
        db.session.add(proposal)
        db.session.flush()

    _audit(
        job.id,
        "assistant_message",
        "Assistant responded to job question",
        {
            "context": context,
            "proposal_id": proposal.id if proposal else None,
            "proposed_change_count": len(proposal_changes),
        },
    )
    db.session.commit()
    return jsonify({"message": answer, "proposal": _proposal_dict(proposal)})


@bp.post("/<int:job_id>/proposals/<int:proposal_id>/apply")
def apply_assistant_proposal(job_id: int, proposal_id: int):
    job = Job.query.get_or_404(job_id)
    proposal = AssistantProposalRecord.query.filter_by(
        id=proposal_id,
        job_id=job.id,
    ).first_or_404()

    if proposal.status != "pending":
        return jsonify({"error": f"Proposal is already {proposal.status}."}), 409
    if not job.working_json:
        return jsonify({"error": "This job has no editable working data."}), 409

    try:
        changes = json.loads(proposal.changes_json)
    except json.JSONDecodeError:
        return jsonify({"error": "Proposal change data is invalid."}), 409

    packing = load_packing(job.working_json)
    applied = []
    try:
        for change in changes:
            packing, result = set_field(
                packing,
                str(change.get("path") or ""),
                change.get("value"),
                unit=change.get("unit"),
                actor="assistant-approved",
                reason=str(change.get("reason") or "Approved assistant proposal"),
            )
            applied.append(result)
    except (WorkingDataError, ValueError, TypeError) as exc:
        return jsonify({"error": f"Proposal can no longer be safely applied: {exc}"}), 409

    _save_working(job, packing)
    proposal.status = "applied"
    proposal.decided_at = datetime.now(timezone.utc)
    proposal.decided_by = "user"
    _audit(
        job.id,
        "assistant_proposal_applied",
        f"Applied assistant proposal {proposal.id}",
        {
            "proposal_id": proposal.id,
            "changes": applied,
            "issues": issue_counts(packing),
        },
        actor="user",
    )
    db.session.commit()
    return jsonify(
        {
            "ok": True,
            "proposal": _proposal_dict(proposal),
            "issue_counts": issue_counts(packing),
            "status": job.status,
        }
    )


@bp.post("/<int:job_id>/proposals/<int:proposal_id>/reject")
def reject_assistant_proposal(job_id: int, proposal_id: int):
    job = Job.query.get_or_404(job_id)
    proposal = AssistantProposalRecord.query.filter_by(
        id=proposal_id,
        job_id=job.id,
    ).first_or_404()

    if proposal.status != "pending":
        return jsonify({"error": f"Proposal is already {proposal.status}."}), 409

    proposal.status = "rejected"
    proposal.decided_at = datetime.now(timezone.utc)
    proposal.decided_by = "user"
    _audit(
        job.id,
        "assistant_proposal_rejected",
        f"Rejected assistant proposal {proposal.id}",
        {"proposal_id": proposal.id},
        actor="user",
    )
    db.session.commit()
    return jsonify({"ok": True, "proposal": _proposal_dict(proposal)})


@bp.get("/<int:job_id>/source-evidence")
def source_evidence(job_id: int):
    Job.query.get_or_404(job_id)
    locator = str(request.args.get("locator") or "").strip()
    if not locator:
        return jsonify({"error": "A source locator is required."}), 400

    matches = find_source_evidence(job_id, locator, limit=5)
    if not matches:
        return jsonify(
            {
                "locator": locator,
                "matches": [],
                "message": "No retained source section matched this locator.",
            }
        ), 404

    return jsonify({"locator": locator, "matches": matches})


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
                    "proposal": _proposal_dict(row.proposal),
                }
                for row in messages
            ]
        }
    )

