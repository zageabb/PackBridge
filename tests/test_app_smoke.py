from pathlib import Path

from packbridge import create_app
from packbridge.config import Config
from packbridge.extensions import db
from packbridge.models import Job


def test_jobs_projects_and_knowledge_pages_render(tmp_path):
    TestConfig = type(
        "TestConfig",
        (Config,),
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "test.sqlite3"),
            "DATA_ROOT": tmp_path / "data",
            "KNOWLEDGE_ROOT": tmp_path / "knowledge",
            "TEMPLATE_ROOT": tmp_path / "templates",
        },
    )
    (tmp_path / "knowledge" / "system").mkdir(parents=True)
    (tmp_path / "knowledge" / "system" / "test.md").write_text(
        "# Test Knowledge\n\nMapping guidance.",
        encoding="utf-8",
    )

    app = create_app(TestConfig)
    client = app.test_client()

    assert client.get("/").status_code == 200
    assert client.get("/projects/").status_code == 200
    assert client.get("/knowledge/").status_code == 200

    response = client.post(
        "/projects/",
        data={"name": "Test SSD Project", "reference": "P-1"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Test SSD Project" in response.data


def test_mapped_job_can_be_attached_to_project(tmp_path):
    TestConfig = type(
        "TestConfig",
        (Config,),
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "test.sqlite3"),
            "DATA_ROOT": tmp_path / "data",
            "KNOWLEDGE_ROOT": tmp_path / "knowledge",
            "TEMPLATE_ROOT": tmp_path / "templates",
        },
    )
    app = create_app(TestConfig)

    from packbridge.schemas import FieldValue, Package, PackingList, SourceValue, WorkingValue

    def field(value):
        return FieldValue(
            source=SourceValue(value=value),
            working=WorkingValue(value=value, origin="source"),
        )

    with app.app_context():
        packing = PackingList(
            packages=[
                Package(
                    case_number=field("CASE-1"),
                    gross_weight=field(10),
                    net_weight=field(9),
                )
            ]
        )
        job = Job(title="Mapped Job", status="mapped", working_json=packing.model_dump_json())
        db.session.add(job)
        db.session.commit()
        job_id = job.id

    client = app.test_client()
    create = client.post("/projects/", data={"name": "Project A"}, follow_redirects=False)
    project_id = int(create.headers["Location"].rstrip("/").split("/")[-1])

    response = client.post(
        f"/projects/{project_id}/jobs",
        data={"job_id": job_id},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Mapped Job" in response.data
    assert b"CASE-1" in response.data



def test_case_specific_ssd_override_round_trip(tmp_path):
    TestConfig = type(
        "TestConfig",
        (Config,),
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "test.sqlite3"),
            "DATA_ROOT": tmp_path / "data",
            "KNOWLEDGE_ROOT": tmp_path / "knowledge",
            "TEMPLATE_ROOT": tmp_path / "templates",
        },
    )
    app = create_app(TestConfig)

    from packbridge.schemas import FieldValue, Package, PackingList, SourceValue, WorkingValue

    def field(value):
        return FieldValue(
            source=SourceValue(value=value),
            working=WorkingValue(value=value, origin="source"),
        )

    with app.app_context():
        packing = PackingList(
            packages=[
                Package(
                    case_number=field("CASE-OVERRIDE"),
                    gross_weight=field(10),
                    net_weight=field(9),
                )
            ]
        )
        job = Job(title="Override Job", status="mapped", working_json=packing.model_dump_json())
        db.session.add(job)
        db.session.commit()
        job_id = job.id

    client = app.test_client()
    response = client.post(
        f"/jobs/{job_id}/ssd-context/case",
        data={
            "case_number": "CASE-OVERRIDE",
            "case_packaging_material": "WOODEN_BOX",
            "case_stackability": "Not stackable",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"override active" in response.data
    assert b"WOODEN_BOX" in response.data

    reset = client.post(
        f"/jobs/{job_id}/ssd-context/case/reset",
        data={"case_number": "CASE-OVERRIDE"},
        follow_redirects=True,
    )
    assert reset.status_code == 200
    assert b"override active" not in reset.data



def test_assistant_proposal_requires_explicit_apply_or_reject(tmp_path):
    TestConfig = type(
        "TestConfig",
        (Config,),
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "test.sqlite3"),
            "DATA_ROOT": tmp_path / "data",
            "KNOWLEDGE_ROOT": tmp_path / "knowledge",
            "TEMPLATE_ROOT": tmp_path / "templates",
        },
    )
    app = create_app(TestConfig)

    from packbridge.models import AssistantProposalRecord, ChatMessage
    from packbridge.schemas import FieldValue, Package, PackingList, SourceValue, WorkingValue
    import json

    def field(value, unit=None):
        return FieldValue(
            source=SourceValue(value=value, unit=unit),
            working=WorkingValue(value=value, unit=unit, origin="source"),
        )

    with app.app_context():
        packing = PackingList(
            packages=[
                Package(
                    case_number=field("CASE-1"),
                    gross_weight=field(10, "KG"),
                    net_weight=field(9, "KG"),
                )
            ]
        )
        job = Job(title="Proposal Job", status="mapped", working_json=packing.model_dump_json())
        db.session.add(job)
        db.session.flush()
        message = ChatMessage(job_id=job.id, role="assistant", content="I can propose that change.")
        db.session.add(message)
        db.session.flush()
        proposal = AssistantProposalRecord(
            job_id=job.id,
            assistant_message_id=message.id,
            status="pending",
            changes_json=json.dumps(
                [
                    {
                        "path": "packages[0].gross_weight",
                        "value": 12,
                        "unit": "KG",
                        "reason": "User asked to correct the gross weight.",
                        "before": {"value": 10, "unit": "KG", "modified": False},
                    }
                ]
            ),
        )
        db.session.add(proposal)
        db.session.commit()
        job_id = job.id
        proposal_id = proposal.id

    client = app.test_client()

    # Merely creating the proposal does not mutate working data.
    with app.app_context():
        unchanged = Job.query.get(job_id)
        current = PackingList.model_validate_json(unchanged.working_json)
        assert current.packages[0].gross_weight.working.value == 10

    applied = client.post(
        f"/jobs/{job_id}/proposals/{proposal_id}/apply",
        json={},
    )
    assert applied.status_code == 200
    assert applied.get_json()["proposal"]["status"] == "applied"

    with app.app_context():
        changed = Job.query.get(job_id)
        current = PackingList.model_validate_json(changed.working_json)
        assert current.packages[0].gross_weight.source.value == 10
        assert current.packages[0].gross_weight.working.value == 12
        assert current.packages[0].gross_weight.modified is True

        reject_message = ChatMessage(job_id=job_id, role="assistant", content="Another proposal")
        db.session.add(reject_message)
        db.session.flush()
        rejected_proposal = AssistantProposalRecord(
            job_id=job_id,
            assistant_message_id=reject_message.id,
            status="pending",
            changes_json=json.dumps(
                [
                    {
                        "path": "packages[0].net_weight",
                        "value": 8,
                        "unit": "KG",
                        "reason": "Test rejection",
                        "before": {"value": 9, "unit": "KG", "modified": False},
                    }
                ]
            ),
        )
        db.session.add(rejected_proposal)
        db.session.commit()
        rejected_id = rejected_proposal.id

    rejected = client.post(
        f"/jobs/{job_id}/proposals/{rejected_id}/reject",
        json={},
    )
    assert rejected.status_code == 200
    assert rejected.get_json()["proposal"]["status"] == "rejected"

    with app.app_context():
        unchanged = Job.query.get(job_id)
        current = PackingList.model_validate_json(unchanged.working_json)
        assert current.packages[0].net_weight.working.value == 9



def test_source_evidence_endpoint_returns_retained_chunk(tmp_path):
    TestConfig = type(
        "TestConfig",
        (Config,),
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "test.sqlite3"),
            "DATA_ROOT": tmp_path / "data",
            "KNOWLEDGE_ROOT": tmp_path / "knowledge",
            "TEMPLATE_ROOT": tmp_path / "templates",
        },
    )
    app = create_app(TestConfig)

    from packbridge.models import SourceChunk, SourceDocument

    with app.app_context():
        job = Job(title="Evidence Route", status="mapped")
        db.session.add(job)
        db.session.flush()
        document = SourceDocument(
            job_id=job.id,
            original_name="packing.pdf",
            stored_name="packing.pdf",
            path="/tmp/packing.pdf",
            size_bytes=1,
            sha256="c" * 64,
            extraction_status="complete",
        )
        db.session.add(document)
        db.session.flush()
        db.session.add(
            SourceChunk(
                document_id=document.id,
                position=14,
                locator="Page 14",
                text="Case CASE-1 Gross Weight 830 KG",
            )
        )
        db.session.commit()
        job_id = job.id

    client = app.test_client()
    response = client.get(f"/jobs/{job_id}/source-evidence?locator=Page%2014")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["matches"][0]["locator"] == "Page 14"
    assert "830 KG" in payload["matches"][0]["text"]
