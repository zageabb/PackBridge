from __future__ import annotations

import shutil
from pathlib import Path

from packbridge.extensions import db
from packbridge.models import (
    AssistantProposalRecord,
    Job,
    KnowledgeProposalRecord,
    SSDContextRecord,
    SSDProjectJob,
    ValidationAcknowledgement,
)


DELETABLE_FAILED_STATUSES = {"failed", "mapping_failed"}


class JobDeletionError(ValueError):
    pass


def can_delete_failed_job(job: Job) -> bool:
    return job.status in DELETABLE_FAILED_STATUSES


def delete_failed_job(job: Job) -> None:
    if not can_delete_failed_job(job):
        raise JobDeletionError(
            "Only jobs in failed or mapping_failed state can be deleted from this action."
        )

    if SSDProjectJob.query.filter_by(job_id=job.id).first() is not None:
        raise JobDeletionError(
            "This failed job is attached to an SSD Project. Remove it from the project first."
        )

    # Knowledge proposals may intentionally outlive the job; retain them but
    # sever the job reference before deleting the parent record.
    KnowledgeProposalRecord.query.filter_by(job_id=job.id).update(
        {"job_id": None},
        synchronize_session=False,
    )

    # Explicitly remove one-to-one/dependent rows whose ORM relationships do not
    # declare delete-orphan cascades. Source/chat/audit rows are cascade-owned by Job.
    SSDContextRecord.query.filter_by(job_id=job.id).delete(synchronize_session=False)
    ValidationAcknowledgement.query.filter_by(job_id=job.id).delete(synchronize_session=False)
    AssistantProposalRecord.query.filter_by(job_id=job.id).delete(synchronize_session=False)

    db.session.delete(job)


def delete_job_files(data_root: Path, job_id: int) -> None:
    root = (Path(data_root).resolve() / "jobs").resolve()
    target = (root / str(job_id)).resolve()

    if root != target and root not in target.parents:
        raise JobDeletionError("Resolved job path is outside PackBridge job storage.")

    if target.is_dir():
        shutil.rmtree(target)
