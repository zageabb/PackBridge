from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from packbridge.models import ValidationAcknowledgement
from packbridge.schemas import MappingIssue, PackingList


def issue_fingerprint(issue: MappingIssue) -> str:
    payload = {
        "code": issue.code,
        "severity": issue.severity,
        "message": issue.message,
        "case_number": issue.case_number,
        "field_path": issue.field_path,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def active_acknowledgements(job_id: int) -> dict[str, ValidationAcknowledgement]:
    rows = ValidationAcknowledgement.query.filter_by(job_id=job_id, status="active").all()
    return {row.issue_fingerprint: row for row in rows}


def apply_acknowledgements(
    packing: PackingList,
    acknowledgements: dict[str, ValidationAcknowledgement],
) -> PackingList:
    for issue in packing.issues:
        issue.resolved = (
            issue.severity == "WARNING"
            and issue_fingerprint(issue) in acknowledgements
        )
    return packing


def acknowledge_issue(
    job_id: int,
    issue: MappingIssue,
    *,
    reason: str | None = None,
    actor: str = "user",
) -> ValidationAcknowledgement:
    if issue.severity != "WARNING":
        raise ValueError("Only warnings can be acknowledged. Blocking issues must be resolved.")

    fingerprint = issue_fingerprint(issue)
    row = ValidationAcknowledgement.query.filter_by(
        job_id=job_id,
        issue_fingerprint=fingerprint,
    ).first()
    if row is None:
        row = ValidationAcknowledgement(
            job_id=job_id,
            issue_fingerprint=fingerprint,
            issue_code=issue.code,
            severity=issue.severity,
            case_number=issue.case_number,
            field_path=issue.field_path,
            message_snapshot=issue.message,
        )

    row.status = "active"
    row.reason = (reason or "").strip() or None
    row.acknowledged_by = actor
    row.acknowledged_at = datetime.now(timezone.utc)
    row.revoked_by = None
    row.revoked_at = None
    return row


def revoke_acknowledgement(
    acknowledgement: ValidationAcknowledgement,
    *,
    actor: str = "user",
) -> ValidationAcknowledgement:
    acknowledgement.status = "revoked"
    acknowledgement.revoked_by = actor
    acknowledgement.revoked_at = datetime.now(timezone.utc)
    return acknowledgement
