from packbridge.learning_schemas import LearnedFieldAlias, LearnedProfileDraft
from packbridge.services.knowledge_governance import validate_knowledge_content
from packbridge.services.profile_learning import (
    render_profile_markdown,
    slugify,
    suggested_profile_path,
)


def test_learned_profile_renders_valid_governed_markdown(tmp_path):
    draft = LearnedProfileDraft(
        title="ACME Packing List",
        vendor_name="ACME Engineering",
        recognition_indicators=["Packing List", "Crate ID", "Shipping Mass"],
        field_aliases=[
            LearnedFieldAlias(
                source_term="Crate ID",
                canonical_field="package.case_number",
            ),
            LearnedFieldAlias(
                source_term="Shipping Mass",
                canonical_field="package.gross_weight",
            ),
        ],
        continuation_key="package.case_number",
        interpretation_notes=["Repeated Crate ID pages continue the same package."],
    )

    markdown = render_profile_markdown(draft)

    assert "# ACME Packing List" in markdown
    assert "~~~packbridge-yaml" in markdown
    assert "Shipping Mass" in markdown
    assert "package.gross_weight" in markdown
    assert validate_knowledge_content(markdown) == markdown


def test_suggested_profile_path_keeps_existing_layout_separate(tmp_path):
    draft = LearnedProfileDraft(
        title="ACME Packing List",
        vendor_name="ACME Engineering",
    )
    first = tmp_path / "vendors" / "acme-engineering" / "packing-list.md"
    first.parent.mkdir(parents=True)
    first.write_text("# Existing\n", encoding="utf-8")

    path = suggested_profile_path(draft, 42, tmp_path)

    assert path == "vendors/acme-engineering/packing-list-layout-42.md"


def test_slugify_is_filesystem_safe():
    assert slugify("Vendor A / UK & IE") == "vendor-a-uk-ie"
