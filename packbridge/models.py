from __future__ import annotations

from datetime import datetime, timezone

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(40), nullable=False, default="new", index=True)
    title = db.Column(db.String(255), nullable=False, default="Packing List Job")
    vendor = db.Column(db.String(255))
    document_profile = db.Column(db.String(255))
    sales_order = db.Column(db.String(100))
    source_json = db.Column(db.Text)
    working_json = db.Column(db.Text)
    approved_json = db.Column(db.Text)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    documents = db.relationship("SourceDocument", backref="job", cascade="all, delete-orphan", lazy=True)
    messages = db.relationship("ChatMessage", backref="job", cascade="all, delete-orphan", lazy=True)
    audit_events = db.relationship("AuditEvent", backref="job", cascade="all, delete-orphan", lazy=True)


class SourceDocument(db.Model):
    __tablename__ = "source_documents"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False)
    path = db.Column(db.Text, nullable=False)
    media_type = db.Column(db.String(120))
    size_bytes = db.Column(db.Integer, nullable=False, default=0)
    sha256 = db.Column(db.String(64), nullable=False, index=True)
    page_count = db.Column(db.Integer)
    extraction_status = db.Column(db.String(40), nullable=False, default="pending")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    chunks = db.relationship("SourceChunk", backref="document", cascade="all, delete-orphan", lazy=True)


class SourceChunk(db.Model):
    __tablename__ = "source_chunks"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False)
    locator = db.Column(db.String(255), nullable=False)
    text = db.Column(db.Text, nullable=False)


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    context_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class AuditEvent(db.Model):
    __tablename__ = "audit_events"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = db.Column(db.String(80), nullable=False, index=True)
    summary = db.Column(db.String(500), nullable=False)
    payload_json = db.Column(db.Text)
    actor = db.Column(db.String(120), nullable=False, default="system")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class SSDContextRecord(db.Model):
    __tablename__ = "ssd_context_records"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(
        db.Integer,
        db.ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    context_json = db.Column(db.Text, nullable=False, default="{}")
    updated_by = db.Column(db.String(120), nullable=False, default="user")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    job = db.relationship("Job", backref=db.backref("ssd_context_record", uselist=False))


class SSDProject(db.Model):
    __tablename__ = "ssd_projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    reference = db.Column(db.String(120), index=True)
    description = db.Column(db.Text)
    context_json = db.Column(db.Text, nullable=False, default="{}")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    job_links = db.relationship(
        "SSDProjectJob",
        backref="project",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="SSDProjectJob.ordinal, SSDProjectJob.id",
    )


class SSDProjectJob(db.Model):
    __tablename__ = "ssd_project_jobs"
    __table_args__ = (
        db.UniqueConstraint("project_id", "job_id", name="uq_ssd_project_job"),
        db.UniqueConstraint("job_id", name="uq_ssd_job_single_project"),
    )

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("ssd_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id = db.Column(
        db.Integer,
        db.ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ordinal = db.Column(db.Integer, nullable=False, default=0)
    added_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    job = db.relationship("Job", backref=db.backref("ssd_project_link", uselist=False))
