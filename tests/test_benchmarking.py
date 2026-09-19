from pathlib import Path

from packbridge.schemas import (
    FieldValue,
    Package,
    PackingItem,
    PackingList,
    SourceValue,
    WorkingValue,
)
from packbridge.services.benchmarking import compare_expected, load_golden_cases


def field(value, unit=None):
    return FieldValue(
        source=SourceValue(value=value, unit=unit),
        working=WorkingValue(value=value, unit=unit, origin="source"),
    )


def test_compare_expected_scores_packages_fields_items_and_nulls():
    packing = PackingList(
        shipment={"country_of_origin": field(None)},
        packages=[
            Package(
                case_number=field("CASE-1"),
                gross_weight=field(100, "KG"),
                net_weight=field(90, "KG"),
                items=[
                    PackingItem(
                        item_number=field("A-1"),
                        description=field("Widget"),
                        quantity=field(2),
                        uom=field("EA"),
                    )
                ],
            )
        ],
    )
    expected = {
        "packages": [
            {
                "case_number": "CASE-1",
                "gross_weight": 100,
                "net_weight": 90,
                "items": [
                    {
                        "item_number": "A-1",
                        "description": "Widget",
                        "quantity": 2,
                        "uom": "EA",
                    }
                ],
            }
        ],
        "must_be_null": ["shipment.country_of_origin"],
    }

    metrics = compare_expected("case", packing, expected, 1.2)

    assert metrics.mapped_ok is True
    assert metrics.package_count_correct is True
    assert metrics.case_set_correct is True
    assert metrics.field_correct == metrics.field_total == 2
    assert metrics.item_correct == metrics.item_total == 1
    assert metrics.null_correct == metrics.null_total == 1
    assert metrics.errors == []


def test_repository_golden_set_has_multiple_layouts():
    root = Path(__file__).resolve().parents[1] / "benchmarks" / "golden"
    cases = load_golden_cases(root)
    names = {name for name, _, _ in cases}

    assert {"internal-qbank", "external-acme", "external-northstar"} <= names
