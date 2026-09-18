from packbridge import create_app
from packbridge.config import Config
from packbridge.extensions import db
from packbridge.models import Job
from packbridge.schemas import MappingIssue, PackingList
from packbridge.services.validation_acknowledgements import issue_fingerprint


def make_app(tmp_path):
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
    return create_app(TestConfig)


def test_warning_can_be_acknowledged_and_reopened(tmp_path):
    app = make_app(tmp_path)
    warning = MappingIssue(
        code="GROSS_BELOW_NET",
        severity="WARNING",
        message="Gross weight (80) is lower than net weight (90).",
        case_number="CASE-1",
        field_path="packages[0].gross_weight",
    )
    packing = PackingList(issues=[warning])

    with app.app_context():
        job = Job(title="Warning Governance", status="mapped", working_json=packing.model_dump_json())
        db.session.add(job)
        db.session.commit()
        job_id = job.id

    client = app.test_client()
    fingerprint = issue_fingerprint(warning)

    response = client.post(
        f"/jobs/{job_id}/issues/acknowledge",
        json={"fingerprint": fingerprint, "reason": "Verified against physical packing data."},
    )
    assert response.status_code == 200
    assert response.get_json()["issue_counts"]["WARNING"] == 0
    assert response.get_json()["resolved_warning_count"] == 1

    page = client.get(f"/jobs/{job_id}")
    assert page.status_code == 200
    assert b"ACKNOWLEDGED" in page.data

    reopened = client.post(
        f"/jobs/{job_id}/issues/reopen",
        json={"fingerprint": fingerprint},
    )
    assert reopened.status_code == 200

    page = client.get(f"/jobs/{job_id}")
    assert b"ACKNOWLEDGED" not in page.data


def test_blocking_issue_cannot_be_acknowledged(tmp_path):
    app = make_app(tmp_path)
    issue = MappingIssue(
        code="CASE_NUMBER_MISSING",
        severity="BLOCKING",
        message="Package 1 has no case/package identifier.",
        field_path="packages[0].case_number",
    )
    packing = PackingList(issues=[issue])

    with app.app_context():
        job = Job(title="Blocking Governance", status="mapped", working_json=packing.model_dump_json())
        db.session.add(job)
        db.session.commit()
        job_id = job.id

    response = app.test_client().post(
        f"/jobs/{job_id}/issues/acknowledge",
        json={"fingerprint": issue_fingerprint(issue), "reason": "Try to ignore"},
    )
    assert response.status_code == 400
    assert "Blocking issues must be resolved" in response.get_json()["error"]
