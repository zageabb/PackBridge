from pathlib import Path

import pytest

from packbridge import create_app
from packbridge.config import Config
from packbridge.extensions import db
from packbridge.models import Job, KnowledgeProposalRecord
from packbridge.services.job_deletion import (
    JobDeletionError,
    delete_failed_job,
    delete_job_files,
)


def make_app(tmp_path):
    TestConfig = type(
        "TestConfig",
        (Config,),
        {
            "TESTING": True,
            "AUTH_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "test.sqlite3"),
            "DATA_ROOT": tmp_path / "data",
            "KNOWLEDGE_ROOT": tmp_path / "knowledge",
            "TEMPLATE_ROOT": tmp_path / "templates",
            "LOG_ROOT": tmp_path / "logs",
            "BACKUP_ROOT": tmp_path / "backups",
        },
    )
    return create_app(TestConfig)


def test_failed_job_can_be_deleted_but_knowledge_proposal_is_retained(tmp_path):
    app = make_app(tmp_path)

    with app.app_context():
        job = Job(title="Bad upload", status="failed", error_message="broken")
        db.session.add(job)
        db.session.flush()
        proposal = KnowledgeProposalRecord(
            job_id=job.id,
            target_path="vendors/acme/packing-list.md",
            base_sha256="a" * 64,
            proposed_content="# ACME\n",
            summary="Retain me",
        )
        db.session.add(proposal)
        db.session.commit()
        job_id = job.id
        proposal_id = proposal.id

        delete_failed_job(job)
        db.session.commit()

        assert db.session.get(Job, job_id) is None
        retained = db.session.get(KnowledgeProposalRecord, proposal_id)
        assert retained is not None
        assert retained.job_id is None


def test_successful_job_cannot_be_deleted_by_failed_job_action(tmp_path):
    app = make_app(tmp_path)

    with app.app_context():
        job = Job(title="Good", status="mapped")
        db.session.add(job)
        db.session.commit()

        with pytest.raises(JobDeletionError):
            delete_failed_job(job)


def test_job_file_cleanup_only_removes_selected_job_folder(tmp_path):
    root = tmp_path / "data"
    target = root / "jobs" / "7"
    other = root / "jobs" / "8"
    target.mkdir(parents=True)
    other.mkdir(parents=True)
    (target / "source.pdf").write_text("x", encoding="utf-8")

    delete_job_files(root, 7)

    assert not target.exists()
    assert other.exists()
