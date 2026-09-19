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
from packbridge.services.working_data import load_packing


def field(value, unit=None, locator="Page 1", modified=False):
    return FieldValue(
        source=SourceValue(
            value=value,
            unit=unit,
            raw=str(value),
            evidence=[Evidence(locator=locator, raw_text=str(value), status="CONFIRMED")],
        ),
        working=WorkingValue(
            value=value,
            unit=unit,
            origin="user_edit" if modified else "source",
            modified_by="user" if modified else None,
        ),
        modified=modified,
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


def add_job(app, tmp_path, *, modified=False):
    packing = PackingList(
        packages=[
            Package(
                case_number=field("CASE-1"),
                gross_weight=field(100, "KG", modified=modified),
                net_weight=field(90, "KG"),
            )
        ]
    )
    with app.app_context():
        job = Job(
            title="Reprocess",
            status="edited" if modified else "mapped",
            source_json=packing.model_dump_json(),
            working_json=packing.model_dump_json(),
        )
        db.session.add(job)
        db.session.flush()

        source = tmp_path / "data" / "jobs" / str(job.id) / "source" / "packing.pdf"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"%PDF-1.4")
        document = SourceDocument(
            job_id=job.id,
            original_name="packing.pdf",
            stored_name="packing.pdf",
            path=str(source),
            size_bytes=8,
            sha256="f" * 64,
            page_count=1,
            extraction_status="complete",
        )
        db.session.add(document)
        db.session.flush()
        db.session.add(
            SourceChunk(
                document_id=document.id,
                position=1,
                locator="Page 1",
                text="Case Number CASE-1 Gross Weight 120 KG Net Weight 90 KG",
            )
        )
        db.session.commit()
        return job.id


def remapped():
    return PackingList(
        packages=[
            Package(
                case_number=field("CASE-1"),
                gross_weight=field(120, "KG"),
                net_weight=field(90, "KG"),
            )
        ]
    )


def test_field_reprocess_replaces_mapped_source_and_working_value(tmp_path, monkeypatch):
    app = make_app(tmp_path)
    job_id = add_job(app, tmp_path)
    monkeypatch.setattr("packbridge.routes.jobs.map_packing_list", lambda *a, **k: remapped())

    response = app.test_client().post(
        f"/jobs/{job_id}/field/reprocess",
        json={"path": "packages[0].gross_weight"},
    )
    assert response.status_code == 200

    with app.app_context():
        job = db.session.get(Job, job_id)
        packing = load_packing(job.working_json)
        assert packing.packages[0].gross_weight.source.value == 120
        assert packing.packages[0].gross_weight.working.value == 120
        assert packing.packages[0].gross_weight.modified is False


def test_reprocess_requires_confirmation_before_discarding_manual_edit(tmp_path, monkeypatch):
    app = make_app(tmp_path)
    job_id = add_job(app, tmp_path, modified=True)
    monkeypatch.setattr("packbridge.routes.jobs.map_packing_list", lambda *a, **k: remapped())

    response = app.test_client().post(
        f"/jobs/{job_id}/field/reprocess",
        json={"path": "packages[0].gross_weight"},
    )
    assert response.status_code == 409

    response = app.test_client().post(
        f"/jobs/{job_id}/field/reprocess",
        json={"path": "packages[0].gross_weight", "discard_edit": True},
    )
    assert response.status_code == 200
