from packbridge import create_app
from packbridge.config import Config
from packbridge.extensions import db
from packbridge.models import Job, SourceChunk, SourceDocument
from packbridge.services.source_evidence import find_source_evidence


def test_source_evidence_prefers_exact_locator(tmp_path):
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
        job = Job(title="Evidence", status="mapped")
        db.session.add(job)
        db.session.flush()
        document = SourceDocument(
            job_id=job.id,
            original_name="source.pdf",
            stored_name="source.pdf",
            path="/tmp/source.pdf",
            size_bytes=1,
            sha256="b" * 64,
            extraction_status="complete",
        )
        db.session.add(document)
        db.session.flush()
        db.session.add_all(
            [
                SourceChunk(document_id=document.id, position=1, locator="Page 1", text="first"),
                SourceChunk(document_id=document.id, position=2, locator="Page 1, part 2", text="second"),
            ]
        )
        db.session.commit()

        results = find_source_evidence(job.id, "Page 1")

        assert [item["locator"] for item in results] == ["Page 1", "Page 1, part 2"]



def test_pdf_page_route_renders_retained_source(tmp_path):
    import fitz

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
        job = Job(title="Rendered Evidence", status="mapped")
        db.session.add(job)
        db.session.flush()

        source_dir = tmp_path / "data" / "jobs" / str(job.id) / "source"
        source_dir.mkdir(parents=True)
        source = source_dir / "packing.pdf"
        pdf = fitz.open()
        page = pdf.new_page(width=300, height=200)
        page.insert_text((30, 60), "Case CASE-1 Gross Weight 830 KG")
        pdf.save(source)
        pdf.close()

        document = SourceDocument(
            job_id=job.id,
            original_name="packing.pdf",
            stored_name="packing.pdf",
            path=str(source),
            size_bytes=source.stat().st_size,
            sha256="d" * 64,
            page_count=1,
            extraction_status="complete",
        )
        db.session.add(document)
        db.session.commit()
        job_id = job.id
        document_id = document.id

    response = app.test_client().get(
        f"/jobs/{job_id}/documents/{document_id}/pages/1.png"
    )

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data.startswith(b"\x89PNG")
