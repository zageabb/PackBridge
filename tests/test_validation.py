from packbridge.schemas import (
    FieldValue,
    Package,
    PackingItem,
    PackingList,
    WorkingValue,
)
from packbridge.services.validation import validate_packing_list


def field(value, unit=None):
    return FieldValue(working=WorkingValue(value=value, unit=unit, origin="source"))


def issue_codes(packing):
    return {issue.code for issue in packing.issues}


def test_duplicate_cases_are_blocking():
    packing = PackingList(
        packages=[
            Package(
                case_number=field("C-1"),
                gross_weight=field(100, "KG"),
                net_weight=field(90, "KG"),
            ),
            Package(
                case_number=field("C-1"),
                gross_weight=field(110, "KG"),
                net_weight=field(95, "KG"),
            ),
        ]
    )

    validate_packing_list(packing)

    duplicate = next(issue for issue in packing.issues if issue.code == "CASE_NUMBER_DUPLICATE")
    assert duplicate.severity == "BLOCKING"


def test_gross_below_net_is_warning():
    packing = PackingList(
        packages=[
            Package(
                case_number=field("C-2"),
                gross_weight=field(80, "KG"),
                net_weight=field(90, "KG"),
            )
        ]
    )

    validate_packing_list(packing)

    warning = next(issue for issue in packing.issues if issue.code == "GROSS_BELOW_NET")
    assert warning.severity == "WARNING"


def test_quantity_without_uom_is_reported():
    packing = PackingList(
        packages=[
            Package(
                case_number=field("C-3"),
                gross_weight=field(100, "KG"),
                net_weight=field(90, "KG"),
                items=[PackingItem(quantity=field(4))],
            )
        ]
    )

    validate_packing_list(packing)

    assert "ITEM_UOM_MISSING" in issue_codes(packing)
