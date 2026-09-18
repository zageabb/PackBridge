from packbridge import create_app
from packbridge.config import Config
from packbridge.extensions import db
from packbridge.models import Job
from packbridge.schemas import MappingIssue, PackingList
from packbridge.services.validation_acknowledgements import (
    acknowledge_issue,
    active_acknowledgements,
    apply_acknowledgements,
    issue_fingerprint,
)


def test_warning_acknowledgement_is_scoped_to_exact_issue_snapshot(tmp_path):
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

    with app.app_context():
        job = Job(title="Warnings", status="mapped")
        db.session.add(job)
        db.session.flush()

        warning = MappingIssue(
            code="GROSS_BELOW_NET",
            severity="WARNING",
            message="Gross weight (80) is lower than net weight (90).",
            case_number="C-1",
            field_path="packages[0].gross_weight",
        )
        row = acknowledge_issue(job.id, warning, reason="Physically verified")
        db.session.add(row)
        db.session.commit()

        packing = PackingList(issues=[warning])
        apply_acknowledgements(packing, active_acknowledgements(job.id))
        assert packing.issues[0].resolved is True

        changed_warning = MappingIssue(
            code="GROSS_BELOW_NET",
            severity="WARNING",
            message="Gross weight (81) is lower than net weight (90).",
            case_number="C-1",
            field_path="packages[0].gross_weight",
        )
        assert issue_fingerprint(changed_warning) != issue_fingerprint(warning)
        packing = PackingList(issues=[changed_warning])
        apply_acknowledgements(packing, active_acknowledgements(job.id))
        assert packing.issues[0].resolved is False
