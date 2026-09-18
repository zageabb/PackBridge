from packbridge import create_app
from packbridge.config import Config
from packbridge.extensions import db
from packbridge.models import Job, KnowledgeProposalRecord
from packbridge.schemas import (
    Evidence,
    FieldValue,
    Package,
    PackingList,
    SourceValue,
    WorkingValue,
)


def make_app(tmp_path):
    knowledge = tmp_path / "knowledge"
    profile = knowledge / "vendors" / "example" / "packing-list.md"
    profile.parent.mkdir(parents=True)
    profile.write_text(
        "# Example Packing List\n\nVersion: 1\n\n"
        "## Typical recognition indicators\n\n"
        "- Packing List\n- Case Number\n- Gross Weight\n\n"
        "## Field Mapping\n\n"
        "Existing guidance.\n",
        encoding="utf-8",
    )
    TestConfig = type(
        "TestConfig",
        (Config,),
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "test.sqlite3"),
            "DATA_ROOT": tmp_path / "data",
            "KNOWLEDGE_ROOT": knowledge,
            "TEMPLATE_ROOT": tmp_path / "templates",
        },
    )
    return create_app(TestConfig), profile


def test_corrected_field_can_create_reviewable_profile_learning_proposal(tmp_path):
    app, profile = make_app(tmp_path)

    corrected = FieldValue(
        source=SourceValue(
            value=100,
            unit="KG",
            raw="Shipping Mass: 100 KG",
            evidence=[
                Evidence(
                    locator="Page 1",
                    raw_text="Shipping Mass: 100 KG",
                    status="SUPPORTED",
                )
            ],
        ),
        working=WorkingValue(
            value=110,
            unit="KG",
            origin="user_edit",
            modified_by="user",
            reason="Verified corrected source interpretation",
        ),
        modified=True,
    )
    packing = PackingList(
        packages=[
            Package(
                case_number=FieldValue(
                    source=SourceValue(value="CASE-1"),
                    working=WorkingValue(value="CASE-1", origin="source"),
                ),
                gross_weight=corrected,
                net_weight=FieldValue(
                    source=SourceValue(value=90, unit="KG"),
                    working=WorkingValue(value=90, unit="KG", origin="source"),
                ),
            )
        ]
    )

    with app.app_context():
        job = Job(
            title="Learning Job",
            status="edited",
            document_profile="Example Packing List",
            working_json=packing.model_dump_json(),
        )
        db.session.add(job)
        db.session.commit()
        job_id = job.id

    original = profile.read_text(encoding="utf-8")
    response = app.test_client().post(
        f"/jobs/{job_id}/learning/propose-field",
        json={
            "path": "packages[0].gross_weight",
            "note": "Shipping Mass should be interpreted using the confirmed correction.",
        },
    )

    assert response.status_code == 200
    assert profile.read_text(encoding="utf-8") == original

    with app.app_context():
        proposal = KnowledgeProposalRecord.query.one()
        assert proposal.status == "pending"
        assert proposal.target_path == "vendors/example/packing-list.md"
        assert "Learned Mapping Examples" in proposal.proposed_content
        assert "packages[0].gross_weight" in proposal.proposed_content
        assert "Shipping Mass: 100 KG" in proposal.proposed_content


def test_unmodified_field_is_not_promoted_to_profile_learning(tmp_path):
    app, _ = make_app(tmp_path)
    packing = PackingList(
        packages=[
            Package(
                case_number=FieldValue(
                    source=SourceValue(value="CASE-1"),
                    working=WorkingValue(value="CASE-1", origin="source"),
                ),
                gross_weight=FieldValue(
                    source=SourceValue(value=100, unit="KG"),
                    working=WorkingValue(value=100, unit="KG", origin="source"),
                ),
                net_weight=FieldValue(
                    source=SourceValue(value=90, unit="KG"),
                    working=WorkingValue(value=90, unit="KG", origin="source"),
                ),
            )
        ]
    )

    with app.app_context():
        job = Job(
            title="Learning Job",
            status="mapped",
            document_profile="Example Packing List",
            working_json=packing.model_dump_json(),
        )
        db.session.add(job)
        db.session.commit()
        job_id = job.id

    response = app.test_client().post(
        f"/jobs/{job_id}/learning/propose-field",
        json={"path": "packages[0].gross_weight", "note": "No correction"},
    )
    assert response.status_code == 400
    assert "Change the field first" in response.get_json()["error"]


def test_unrecognised_job_can_draft_inactive_profile_proposal(tmp_path, monkeypatch):
    from packbridge.learning_schemas import LearnedFieldAlias, LearnedProfileDraft
    from packbridge.models import SourceChunk, SourceDocument

    app, _ = make_app(tmp_path)
    packing = PackingList(
        document={"vendor": "New Supplier"},
        packages=[
            Package(
                case_number=FieldValue(
                    source=SourceValue(value="CASE-9"),
                    working=WorkingValue(value="CASE-9", origin="source"),
                ),
                gross_weight=FieldValue(
                    source=SourceValue(value=120, unit="KG"),
                    working=WorkingValue(value=120, unit="KG", origin="source"),
                ),
                net_weight=FieldValue(
                    source=SourceValue(value=100, unit="KG"),
                    working=WorkingValue(value=100, unit="KG", origin="source"),
                ),
            )
        ],
    )

    with app.app_context():
        job = Job(
            title="New Supplier Packing List",
            status="mapped",
            vendor="New Supplier",
            working_json=packing.model_dump_json(),
        )
        db.session.add(job)
        db.session.flush()
        source_path = tmp_path / "data" / "jobs" / str(job.id) / "source" / "packing.pdf"
        source_path.parent.mkdir(parents=True)
        source_path.write_bytes(b"%PDF-1.4 test")
        document = SourceDocument(
            job_id=job.id,
            original_name="packing.pdf",
            stored_name="packing.pdf",
            path=str(source_path),
            size_bytes=12,
            sha256="e" * 64,
            extraction_status="complete",
        )
        db.session.add(document)
        db.session.flush()
        db.session.add(
            SourceChunk(
                document_id=document.id,
                position=1,
                locator="Page 1",
                text="Packing List Crate ID CASE-9 Shipping Mass 120 KG",
            )
        )
        db.session.commit()
        job_id = job.id

    monkeypatch.setattr(
        "packbridge.routes.jobs.draft_profile",
        lambda **kwargs: LearnedProfileDraft(
            title="New Supplier Packing List",
            vendor_name="New Supplier",
            recognition_indicators=["Packing List", "Crate ID", "Shipping Mass"],
            field_aliases=[
                LearnedFieldAlias(
                    source_term="Crate ID",
                    canonical_field="package.case_number",
                )
            ],
            continuation_key="package.case_number",
        ),
    )

    response = app.test_client().post(
        f"/jobs/{job_id}/learning/draft-profile",
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        proposal = KnowledgeProposalRecord.query.order_by(KnowledgeProposalRecord.id.desc()).first()
        assert proposal is not None
        assert proposal.status == "pending"
        assert proposal.target_path == "vendors/new-supplier/packing-list.md"
        assert "Crate ID" in proposal.proposed_content
        assert not (tmp_path / "knowledge" / proposal.target_path).exists()
