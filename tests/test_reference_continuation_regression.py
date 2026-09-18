from packbridge.schemas import FieldValue, Package, PackingList, SourceValue, WorkingValue
from packbridge.services.postprocess import merge_continuation_packages


def field(value):
    return FieldValue(
        source=SourceValue(value=value),
        working=WorkingValue(value=value, origin="source"),
    )


def package(case_number, item_marker):
    from packbridge.schemas import PackingItem

    return Package(
        case_number=field(case_number),
        gross_weight=field(100),
        net_weight=field(90),
        items=[PackingItem(sequence=field(item_marker), item_number=field(f"ITEM-{item_marker}"))],
    )


def test_reference_shape_twenty_page_records_collapse_to_seventeen_cases():
    case_numbers = [str(value) for value in range(48366831, 48366848)]
    mapped_pages = []
    for case_number in case_numbers:
        mapped_pages.append(package(case_number, "1"))
        if case_number in {"48366844", "48366845", "48366846"}:
            mapped_pages.append(package(case_number, "2"))

    assert len(mapped_pages) == 20

    merged, issues, count = merge_continuation_packages(
        PackingList(packages=mapped_pages)
    )

    assert count == 3
    assert len(merged.packages) == 17
    assert [row.case_number.working.value for row in merged.packages] == case_numbers
    assert issues == []
