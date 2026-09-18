from packbridge.schemas import (
    Dimensions,
    FieldValue,
    Package,
    PackingItem,
    PackingList,
    SourceValue,
    WorkingValue,
)
from packbridge.services.postprocess import merge_continuation_packages


def field(value, unit=None):
    return FieldValue(
        source=SourceValue(value=value, unit=unit),
        working=WorkingValue(value=value, unit=unit, origin="source"),
    )


def item(sequence, item_number):
    return PackingItem(
        sequence=field(sequence),
        item_number=field(item_number),
        quantity=field(1),
        uom=field("PC"),
    )


def test_duplicate_case_pages_are_merged_and_items_appended():
    packing = PackingList(
        packages=[
            Package(
                case_number=field("48366844"),
                dimensions=Dimensions(
                    length=field(307),
                    width=field(249),
                    height=field(73),
                    unit="CM",
                ),
                gross_weight=field(875, "KG"),
                net_weight=field(518, "KG"),
                items=[item(1, "A"), item(2, "B")],
            ),
            Package(
                case_number=field("48366844"),
                dimensions=Dimensions(
                    length=field(307),
                    width=field(249),
                    height=field(73),
                    unit="CM",
                ),
                gross_weight=field(875, "KG"),
                net_weight=field(518, "KG"),
                items=[item(3, "C"), item(4, "D")],
            ),
        ]
    )

    merged, issues, count = merge_continuation_packages(packing)

    assert count == 1
    assert len(merged.packages) == 1
    assert [row.item_number.working.value for row in merged.packages[0].items] == ["A", "B", "C", "D"]
    assert issues == []


def test_continuation_conflict_is_warned_not_silently_overwritten():
    packing = PackingList(
        packages=[
            Package(
                case_number=field("CASE-1"),
                gross_weight=field(100, "KG"),
                net_weight=field(80, "KG"),
            ),
            Package(
                case_number=field("CASE-1"),
                gross_weight=field(110, "KG"),
                net_weight=field(80, "KG"),
            ),
        ]
    )

    merged, issues, count = merge_continuation_packages(packing)

    assert count == 1
    assert merged.packages[0].gross_weight.working.value == 100
    assert any(issue.code == "CONTINUATION_FIELD_CONFLICT" for issue in issues)


def test_exact_duplicate_item_is_not_added_twice():
    duplicate = item(1, "A")
    packing = PackingList(
        packages=[
            Package(
                case_number=field("CASE-1"),
                gross_weight=field(10, "KG"),
                net_weight=field(9, "KG"),
                items=[duplicate],
            ),
            Package(
                case_number=field("CASE-1"),
                gross_weight=field(10, "KG"),
                net_weight=field(9, "KG"),
                items=[duplicate.model_copy(deep=True)],
            ),
        ]
    )

    merged, _, _ = merge_continuation_packages(packing)

    assert len(merged.packages[0].items) == 1
