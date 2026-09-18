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
