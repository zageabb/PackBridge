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



def test_missing_and_unknown_units_are_reported():
    packing = PackingList(
        packages=[
            Package(
                case_number=field("C-UNIT"),
                gross_weight=field(100),
                net_weight=field(90, "STONE"),
            )
        ]
    )
    packing.packages[0].dimensions.length = field(10)
    packing.packages[0].dimensions.width = field(20)
    packing.packages[0].dimensions.height = field(30)
    packing.packages[0].dimensions.unit = "CM"

    validate_packing_list(packing)

    codes = issue_codes(packing)
    assert "GROSS_WEIGHT_UNIT_MISSING" in codes
    assert "NET_WEIGHT_UNIT_UNKNOWN" in codes
    assert "DIMENSION_UNIT_MISSING" not in codes


def test_supported_units_do_not_raise_unit_warnings():
    packing = PackingList(
        packages=[
            Package(
                case_number=field("C-OK"),
                gross_weight=field(100, "KG"),
                net_weight=field(90, "KG"),
            )
        ]
    )
    packing.packages[0].dimensions.length = field(100, "MM")
    packing.packages[0].dimensions.width = field(200, "MM")
    packing.packages[0].dimensions.height = field(300, "MM")

    validate_packing_list(packing)

    codes = issue_codes(packing)
    assert not any(code.endswith("_UNIT_MISSING") for code in codes)
    assert not any(code.endswith("_UNIT_UNKNOWN") for code in codes)
