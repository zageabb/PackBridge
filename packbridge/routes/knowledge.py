from __future__ import annotations

from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from packbridge.extensions import db
from packbridge.models import AuditEvent, KnowledgeProposalRecord
from packbridge.services.knowledge import list_documents, search
from packbridge.services.knowledge_governance import (
    KnowledgeGovernanceError,
    apply_proposal,
    current_content,
    proposal_diff,
    reject_proposal,
    safe_knowledge_path,
    sha256_text,
    validate_knowledge_content,
)

bp = Blueprint("knowledge", __name__, url_prefix="/knowledge")


def _root() -> Path:
    return Path(current_app.config["KNOWLEDGE_ROOT"]).resolve()


def _safe_document(root: Path, relative: str) -> Path:
    try:
        return safe_knowledge_path(root, relative, must_exist=True)
    except KnowledgeGovernanceError as exc:
        if "does not exist" in str(exc):
            abort(404)
        abort(400)


def _audit_job(job_id: int | None, event_type: str, summary: str, payload: dict | None = None) -> None:
    if not job_id:
        return
    db.session.add(
        AuditEvent(
            job_id=job_id,
            event_type=event_type,
            summary=summary,
            payload_json=__import__("json").dumps(payload or {}, default=str),
            actor="user",
        )
    )


@bp.get("/")
def index():
    root = _root()
    query = request.args.get("q", "").strip()
    selected_path = request.args.get("path", "").strip()
    job_id_raw = request.args.get("job", "").strip()
    job_id = int(job_id_raw) if job_id_raw.isdigit() else None

    if query:
        hits = search(root, query, limit=50)
        documents = [
            {
                "path": hit.path,
                "title": hit.title,
                "score": hit.score,
            }
            for hit in hits
        ]
    else:
        documents = []
        for path in list_documents(root):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            title = path.stem
            for line in text.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            documents.append(
                {
                    "path": str(path.relative_to(root)),
                    "title": title,
                    "score": None,
                }
            )

    selected = None
    if selected_path:
        path = _safe_document(root, selected_path)
        selected = {
            "path": str(path.relative_to(root)),
            "content": path.read_text(encoding="utf-8"),
        }
    elif documents:
        path = _safe_document(root, documents[0]["path"])
        selected = {
            "path": str(path.relative_to(root)),
            "content": path.read_text(encoding="utf-8"),
        }

    proposal_rows = (
        KnowledgeProposalRecord.query
        .order_by(KnowledgeProposalRecord.created_at.desc())
        .limit(30)
        .all()
    )
    proposals = [
        {
            "record": row,
            "diff": proposal_diff(root, row),
        }
        for row in proposal_rows
    ]

    return render_template(
        "knowledge.html",
        documents=documents,
        selected=selected,
        query=query,
        proposals=proposals,
        job_id=job_id,
    )


@bp.post("/proposals/edit")
def propose_edit():
    root = _root()
    target_path = str(request.form.get("target_path") or "").strip()
    proposed_content = str(request.form.get("proposed_content") or "")
    summary = str(request.form.get("summary") or "").strip()
    reason = str(request.form.get("reason") or "").strip()
    job_id_raw = str(request.form.get("job_id") or "").strip()
    job_id = int(job_id_raw) if job_id_raw.isdigit() else None

    try:
        _, current, base_hash = current_content(root, target_path)
        proposed_content = validate_knowledge_content(proposed_content)
        if proposed_content == current:
            raise KnowledgeGovernanceError("No Knowledge changes were proposed.")
        proposal = KnowledgeProposalRecord(
            job_id=job_id,
            target_path=target_path,
            base_sha256=base_hash,
            proposed_content=proposed_content,
            summary=summary or f"Update {target_path}",
            reason=reason or None,
            created_by="user",
            status="pending",
        )
        db.session.add(proposal)
        db.session.flush()
        _audit_job(
            job_id,
            "knowledge_change_proposed",
            f"Proposed Knowledge change for {target_path}",
            {"proposal_id": proposal.id, "target_path": target_path, "summary": proposal.summary},
        )
        db.session.commit()
        flash("Knowledge change proposed. Review the diff and approve it separately.", "success")
    except (KnowledgeGovernanceError, OSError, ValueError) as exc:
        db.session.rollback()
        flash(str(exc), "danger")

    return redirect(url_for("knowledge.index", path=target_path))


@bp.post("/proposals/new")
def propose_new():
    root = _root()
    target_path = str(request.form.get("target_path") or "").strip()
    proposed_content = str(request.form.get("proposed_content") or "")
    summary = str(request.form.get("summary") or "").strip()
    reason = str(request.form.get("reason") or "").strip()
    job_id_raw = str(request.form.get("job_id") or "").strip()
    job_id = int(job_id_raw) if job_id_raw.isdigit() else None

    try:
        path = safe_knowledge_path(root, target_path, must_exist=False)
        if path.exists():
            raise KnowledgeGovernanceError("A Knowledge document already exists at that path.")
        proposed_content = validate_knowledge_content(proposed_content)

        proposal = KnowledgeProposalRecord(
            job_id=job_id,
            target_path=str(path.relative_to(root)),
            base_sha256=sha256_text(""),
            proposed_content=proposed_content,
            summary=summary or f"Create {path.name}",
            reason=reason or None,
            created_by="user",
            status="pending",
        )
        db.session.add(proposal)
        db.session.flush()
        _audit_job(
            job_id,
            "knowledge_profile_proposed",
            f"Proposed new Knowledge document {proposal.target_path}",
            {"proposal_id": proposal.id, "target_path": proposal.target_path},
        )
        db.session.commit()
        flash("New Knowledge document proposed. It is not active until approved.", "success")
    except (KnowledgeGovernanceError, OSError, ValueError) as exc:
        db.session.rollback()
        flash(str(exc), "danger")

    return redirect(url_for("knowledge.index"))


@bp.get("/download")
def download():
    root = _root()
    target_path = str(request.args.get("path") or "").strip()
    path = _safe_document(root, target_path)
    return send_file(
        path,
        as_attachment=True,
        download_name=path.name,
        mimetype="text/markdown",
    )


@bp.post("/proposals/import")
def propose_import():
    root = _root()
    target_path = str(request.form.get("target_path") or "").strip()
    summary = str(request.form.get("summary") or "").strip()
    reason = str(request.form.get("reason") or "").strip()
    job_id_raw = str(request.form.get("job_id") or "").strip()
    job_id = int(job_id_raw) if job_id_raw.isdigit() else None
    upload = request.files.get("knowledge_file")

    try:
        if upload is None or not upload.filename:
            raise KnowledgeGovernanceError("Choose an updated Markdown Knowledge document.")
        if not upload.filename.casefold().endswith(".md"):
            raise KnowledgeGovernanceError("Knowledge imports must be Markdown (.md) files.")

        payload = upload.stream.read(600_000)
        if upload.stream.read(1):
            raise KnowledgeGovernanceError("Knowledge import exceeds the safety limit.")
        try:
            proposed_content = payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise KnowledgeGovernanceError("Knowledge imports must use UTF-8 text encoding.") from exc

        proposed_content = validate_knowledge_content(proposed_content)
        _, current, base_hash = current_content(root, target_path)
        if proposed_content == current:
            raise KnowledgeGovernanceError("The imported Knowledge file is identical to the active document.")

        proposal = KnowledgeProposalRecord(
            job_id=job_id,
            target_path=target_path,
            base_sha256=base_hash,
            proposed_content=proposed_content,
            summary=summary or f"Import updated {target_path}",
            reason=reason or None,
            created_by="user",
            status="pending",
        )
        db.session.add(proposal)
        db.session.flush()
        _audit_job(
            job_id,
            "knowledge_import_proposed",
            f"Imported proposed Knowledge replacement for {target_path}",
            {
                "proposal_id": proposal.id,
                "target_path": target_path,
                "filename": upload.filename,
            },
        )
        db.session.commit()
        flash("Updated Knowledge file imported as a proposal. Review the diff before approval.", "success")
    except (KnowledgeGovernanceError, OSError, ValueError) as exc:
        db.session.rollback()
        flash(str(exc), "danger")

    return redirect(url_for("knowledge.index", path=target_path, job=job_id or None))


@bp.post("/proposals/<int:proposal_id>/apply")
def apply(proposal_id: int):
    root = _root()
    proposal = KnowledgeProposalRecord.query.get_or_404(proposal_id)

    try:
        apply_proposal(root, proposal, actor="user")
        _audit_job(
            proposal.job_id,
            "knowledge_change_applied",
            f"Applied Knowledge proposal {proposal.id}",
            {
                "proposal_id": proposal.id,
                "target_path": proposal.target_path,
                "applied_sha256": proposal.applied_sha256,
            },
        )
        db.session.commit()
        flash("Knowledge proposal approved and activated.", "success")
    except (KnowledgeGovernanceError, OSError) as exc:
        db.session.rollback()
        flash(str(exc), "danger")

    return redirect(url_for("knowledge.index", path=proposal.target_path))


@bp.post("/proposals/<int:proposal_id>/reject")
def reject(proposal_id: int):
    proposal = KnowledgeProposalRecord.query.get_or_404(proposal_id)

    try:
        reject_proposal(proposal, actor="user")
        _audit_job(
            proposal.job_id,
            "knowledge_change_rejected",
            f"Rejected Knowledge proposal {proposal.id}",
            {"proposal_id": proposal.id, "target_path": proposal.target_path},
        )
        db.session.commit()
        flash("Knowledge proposal rejected.", "success")
    except KnowledgeGovernanceError as exc:
        db.session.rollback()
        flash(str(exc), "danger")

    return redirect(url_for("knowledge.index", path=proposal.target_path))
