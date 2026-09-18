from packbridge.mapper_schemas import (
    MappedItem,
    MappedPackage,
    MappedValue,
    MapperResult,
)
from packbridge.services.mapper import merge_mapper_results, split_mapping_segments


def value(v, status="CONFIRMED"):
    return MappedValue(value=v, raw=str(v), locator="Page 1", status=status)


def test_large_document_splits_on_page_boundaries():
    text = "\n\n".join(
        f"[Page {index}]\n" + ("X" * 9000)
        for index in range(1, 8)
    )

    segments = split_mapping_segments(text, target_chars=25000)

    assert len(segments) >= 3
    assert all(segment.startswith("[Page ") for segment in segments)
    joined = "\n\n".join(segments)
    for index in range(1, 8):
        assert f"[Page {index}]" in joined


def test_mapper_segment_merge_combines_same_case_items():
    first = MapperResult(
        vendor="Example",
        packages=[
            MappedPackage(
                case_number=value("CASE-1"),
                gross_weight=value(100),
                net_weight=value(90),
                items=[
                    MappedItem(
                        sequence=value(1),
                        item_number=value("ITEM-A"),
                        quantity=value(2),
                        uom=value("PC"),
                    )
                ],
            )
        ],
    )
    second = MapperResult(
        vendor="Example",
        packages=[
            MappedPackage(
                case_number=value("CASE-1"),
                gross_weight=value(100),
                net_weight=value(90),
                items=[
                    MappedItem(
                        sequence=value(2),
                        item_number=value("ITEM-B"),
                        quantity=value(4),
                        uom=value("PC"),
                    )
                ],
            )
        ],
    )

    merged, conflicts = merge_mapper_results([first, second])

    assert conflicts == []
    assert len(merged.packages) == 1
    assert merged.packages[0].case_number.value == "CASE-1"
    assert [item.item_number.value for item in merged.packages[0].items] == ["ITEM-A", "ITEM-B"]


def test_mapper_segment_merge_surfaces_conflicting_values():
    first = MapperResult(
        packages=[
            MappedPackage(
                case_number=value("CASE-1"),
                gross_weight=value(100),
            )
        ]
    )
    second = MapperResult(
        packages=[
            MappedPackage(
                case_number=value("CASE-1"),
                gross_weight=value(110),
            )
        ]
    )

    merged, conflicts = merge_mapper_results([first, second])

    assert merged.packages[0].gross_weight.value == 100
    assert len(conflicts) == 1
    assert "gross_weight" in conflicts[0]
