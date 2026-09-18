from packbridge import create_app
from packbridge.config import Config
from packbridge.extensions import db
from packbridge.models import Job, SourceChunk, SourceDocument
from packbridge.schemas import (
    Evidence,
    FieldValue,
    Package,
    PackingList,
    SourceValue,
    WorkingValue,
)
from packbridge.services.assistant_context import build_assistant_context


def field(value, *, locator=None, unit=None):
    evidence = [Evidence(locator=locator, raw_text=str(value), status="CONFIRMED")] if locator else []
    return FieldValue(
        source=SourceValue(value=value, unit=unit, evidence=evidence),
        working=WorkingValue(value=value, unit=unit, origin="source"),
    )


def test_selected_case_context_contains_matching_source_excerpt(tmp_path):
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
        packing = PackingList(
            packages=[
                Package(
                    case_number=field("CASE-1", locator="Page 14"),
                    gross_weight=field(830, locator="Page 14", unit="KG"),
                    net_weight=field(643, locator="Page 14", unit="KG"),
                )
            ]
        )
        job = Job(title="Assistant Context", status="mapped", working_json=packing.model_dump_json())
        db.session.add(job)
        db.session.flush()
        document = SourceDocument(
            job_id=job.id,
            original_name="packing.pdf",
            stored_name="packing.pdf",
            path="/tmp/packing.pdf",
            size_bytes=10,
            sha256="a" * 64,
            extraction_status="complete",
        )
        db.session.add(document)
        db.session.flush()
        db.session.add(
            SourceChunk(
                document_id=document.id,
                position=14,
                locator="Page 14",
                text="Case Number CASE-1 Gross Weight 830 KG Net Weight 643 KG",
            )
        )
        db.session.commit()

        context = build_assistant_context(job, packing, "CASE-1")

        assert context["selected_package"]["case_number"]["working"]["value"] == "CASE-1"
        assert context["source_evidence"][0]["locator"] == "Page 14"
        assert "Gross Weight 830 KG" in context["source_evidence"][0]["text"]
