from packbridge.services.knowledge import context_for, search


def test_knowledge_search_prefers_heading_match(tmp_path):
    (tmp_path / "vendors").mkdir()
    (tmp_path / "vendors" / "abc.md").write_text(
        "# ABC Packing List\n\nShipping Mass means gross weight.",
        encoding="utf-8",
    )
    (tmp_path / "other.md").write_text(
        "# Other Notes\n\nThis note also mentions packing.",
        encoding="utf-8",
    )

    hits = search(tmp_path, "ABC packing gross weight")

    assert hits
    assert hits[0].path == "vendors/abc.md"
    assert "Shipping Mass" in context_for(tmp_path, "ABC gross weight")
