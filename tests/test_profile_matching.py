from packbridge.services.profile_matching import match_profile


def test_profile_match_uses_recognition_indicators(tmp_path):
    root = tmp_path
    profile_dir = root / "vendors" / "example"
    profile_dir.mkdir(parents=True)
    (profile_dir / "packing.md").write_text(
        """# Example Vendor Packing List

## Typical recognition indicators

- Packing List
- Case Number
- Gross Weight
- Net Weight
- Packed By
""",
        encoding="utf-8",
    )

    match = match_profile(
        root,
        "Packing List\nCase Number ABC\nGross Weight 100 KG\nNet Weight 90 KG",
    )

    assert match is not None
    assert match.title == "Example Vendor Packing List"
    assert match.score == 4
    assert match.path == "vendors/example/packing.md"


def test_profile_match_requires_minimum_evidence(tmp_path):
    profile_dir = tmp_path / "vendors" / "example"
    profile_dir.mkdir(parents=True)
    (profile_dir / "packing.md").write_text(
        """# Example

## Typical recognition indicators

- Packing List
- Case Number
- Gross Weight
""",
        encoding="utf-8",
    )

    assert match_profile(tmp_path, "Packing List only") is None
