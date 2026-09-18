from packbridge import create_app
from packbridge.config import Config
from packbridge.extensions import db
from packbridge.models import KnowledgeProposalRecord


def make_app(tmp_path):
    root = tmp_path / "knowledge"
    root.mkdir()
    TestConfig = type(
        "TestConfig",
        (Config,),
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "test.sqlite3"),
            "DATA_ROOT": tmp_path / "data",
            "KNOWLEDGE_ROOT": root,
            "TEMPLATE_ROOT": tmp_path / "templates",
        },
    )
    return create_app(TestConfig), root


def test_existing_knowledge_edit_requires_separate_approval(tmp_path):
    app, root = make_app(tmp_path)
    path = root / "vendor.md"
    path.write_text("# Vendor\n\nOld mapping.\n", encoding="utf-8")

    client = app.test_client()
    response = client.post(
        "/knowledge/proposals/edit",
        data={
            "target_path": "vendor.md",
            "summary": "Update mapping",
            "reason": "Confirmed on new packing list",
            "proposed_content": "# Vendor\n\nNew mapping.\n",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert path.read_text(encoding="utf-8") == "# Vendor\n\nOld mapping.\n"

    with app.app_context():
        proposal = KnowledgeProposalRecord.query.one()
        assert proposal.status == "pending"
        proposal_id = proposal.id

    applied = client.post(
        f"/knowledge/proposals/{proposal_id}/apply",
        follow_redirects=False,
    )
    assert applied.status_code == 302
    assert path.read_text(encoding="utf-8") == "# Vendor\n\nNew mapping.\n"


def test_new_vendor_profile_is_inactive_until_approved(tmp_path):
    app, root = make_app(tmp_path)
    client = app.test_client()

    response = client.post(
        "/knowledge/proposals/new",
        data={
            "target_path": "vendors/acme/packing-list.md",
            "summary": "Add ACME packing-list profile",
            "reason": "New supplier format",
            "proposed_content": "# ACME Packing List\n\n## Field Mapping\n\nShipping Mass = gross weight.\n",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    target = root / "vendors" / "acme" / "packing-list.md"
    assert not target.exists()

    with app.app_context():
        proposal = KnowledgeProposalRecord.query.one()
        proposal_id = proposal.id

    applied = client.post(
        f"/knowledge/proposals/{proposal_id}/apply",
        follow_redirects=False,
    )
    assert applied.status_code == 302
    assert target.exists()
    assert "Shipping Mass" in target.read_text(encoding="utf-8")
