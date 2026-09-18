from packbridge import create_app
from packbridge.config import Config
from packbridge.extensions import db
from packbridge.models import KnowledgeProposalRecord
from packbridge.services.knowledge_governance import (
    KnowledgeGovernanceError,
    apply_proposal,
    current_content,
    proposal_diff,
)


def test_knowledge_proposal_applies_only_when_base_version_matches(tmp_path):
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
    root = tmp_path / "knowledge"
    root.mkdir()
    (root / "vendor.md").write_text("# Vendor\n\nOld guidance.\n", encoding="utf-8")

    app = create_app(TestConfig)
    with app.app_context():
        _, current, base_hash = current_content(root, "vendor.md")
        proposal = KnowledgeProposalRecord(
            target_path="vendor.md",
            base_sha256=base_hash,
            proposed_content="# Vendor\n\nNew guidance.\n",
            summary="Update vendor mapping",
        )
        db.session.add(proposal)
        db.session.commit()

        assert "-Old guidance." in proposal_diff(root, proposal)
        assert "+New guidance." in proposal_diff(root, proposal)

        apply_proposal(root, proposal)
        db.session.commit()

        assert proposal.status == "applied"
        assert (root / "vendor.md").read_text(encoding="utf-8") == "# Vendor\n\nNew guidance.\n"


def test_knowledge_proposal_detects_version_conflict(tmp_path):
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
    root = tmp_path / "knowledge"
    root.mkdir()
    path = root / "vendor.md"
    path.write_text("# Vendor\n\nOld.\n", encoding="utf-8")

    app = create_app(TestConfig)
    with app.app_context():
        _, _, base_hash = current_content(root, "vendor.md")
        proposal = KnowledgeProposalRecord(
            target_path="vendor.md",
            base_sha256=base_hash,
            proposed_content="# Vendor\n\nProposed.\n",
            summary="Change",
        )
        db.session.add(proposal)
        db.session.commit()

        path.write_text("# Vendor\n\nSomeone else changed this.\n", encoding="utf-8")

        try:
            apply_proposal(root, proposal)
            assert False, "expected conflict"
        except KnowledgeGovernanceError:
            pass
