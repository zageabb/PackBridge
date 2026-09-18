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
from packbridge.models import AuditEvent, ChatMessage, Job, SourceChunk, SourceDocument
from packbridge.services.document_ingestion import (
    ALLOWED_EXTENSIONS,
    DocumentIngestionError,
    extract_path,
)
from packbridge.services.mapper import MappingError, map_packing_list
from packbridge.services.prompt_service import load_prompt
from packbridge.services.runtime_settings import client as ollama_client
from packbridge.services.storage import save_job_upload

bp = Blueprint("jobs", __name__, url_prefix="/jobs")


def _audit(job_id: int, event_type: str, summary: str, payload: dict | None = None, actor: str = "system") -> None:
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
        _audit(job.id, "source_uploaded", f"Uploaded {original_name}", {"sha256": digest, "size_bytes": size})

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
    selected_case = request.args.get("case")
    packages = (packing or {}).get("packages", [])
    selected = None
    if packages:
        selected = next(
            (
                package
                for package in packages
                if str(((package.get("case_number") or {}).get("working") or {}).get("value"))
                == selected_case
            ),
            packages[0],
        )
    return render_template(
        "job.html",
        job=job,
        packing=packing,
        packages=packages,
        selected_package=selected,
    )


@bp.post("/<int:job_id>/process")
def process(job_id: int):
    job = Job.query.get_or_404(job_id)
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

    job.status = "processing"
    _audit(job.id, "mapping_started", "Local document mapping started", {"profile_hint": profile_hint})
    db.session.commit()

    try:
        packing = map_packing_list(document_text, profile_hint=profile_hint)
        payload = packing.model_dump_json()
        job.source_json = payload
        job.working_json = payload
        job.vendor = packing.document.vendor
        job.document_profile = packing.document.document_profile
        sales_order = packing.order.sales_order.working.value if packing.order.sales_order.working else None
        job.sales_order = str(sales_order) if sales_order not in (None, "") else None
        job.status = "mapped"
        job.error_message = None
        _audit(
            job.id,
            "mapping_completed",
            f"Mapped {len(packing.packages)} package(s)",
            {"packages": len(packing.packages), "model": ollama_client().model},
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
    system_prompt = load_prompt("job_assistant") + "\n\nCURRENT JOB CONTEXT:\n" + json.dumps(job_context, default=str)[:60_000]
    result = ollama_client().chat(history, system_prompt=system_prompt)

    if result.available:
        answer = str(result.value)
    else:
        answer = f"Local assistant unavailable: {result.warning or result.error_code}"

    db.session.add(ChatMessage(job_id=job.id, role="assistant", content=answer, context_json=json.dumps(context)))
    _audit(job.id, "assistant_message", "Assistant responded to job question", {"context": context})
    db.session.commit()
    return jsonify({"message": answer})


@bp.get("/<int:job_id>/chat/history")
def chat_history(job_id: int):
    Job.query.get_or_404(job_id)
    messages = ChatMessage.query.filter_by(job_id=job_id).order_by(ChatMessage.id).all()
    return jsonify(
        {
            "messages": [
                {"role": row.role, "content": row.content, "created_at": row.created_at.isoformat()}
                for row in messages
            ]
        }
    )
