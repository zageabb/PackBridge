from packbridge.schemas import (
    FieldValue,
    Package,
    PackingItem,
    PackingList,
    SourceValue,
    WorkingValue,
)
from packbridge.services.working_data import (
    get_field,
    has_modifications,
    revert_all,
    revert_field,
    revert_package,
    set_field,
)


def mapped_field(value, unit=None):
    return FieldValue(
        source=SourceValue(value=value, unit=unit),
        working=WorkingValue(value=value, unit=unit, origin="source"),
    )


def sample_packing():
    return PackingList(
        packages=[
            Package(
                case_number=mapped_field("C-1"),
                gross_weight=mapped_field(100, "KG"),
                net_weight=mapped_field(90, "KG"),
                items=[
                    PackingItem(
                        item_number=mapped_field("ITEM-1"),
                        quantity=mapped_field(2),
                        uom=mapped_field("EA"),
                    )
                ],
            )
        ]
    )


def test_set_field_preserves_source_and_marks_working_modified():
    packing = sample_packing()

    packing, change = set_field(
        packing,
        "packages[0].gross_weight",
        "125",
        reason="Corrected from marked-up packing list",
    )

    field = packing.packages[0].gross_weight
    assert field.source.value == 100
    assert field.working.value == 125
    assert field.working.origin == "user_edit"
    assert field.modified is True
    assert change["before"]["value"] == 100
    assert change["after"]["value"] == 125
    assert has_modifications(packing) is True


def test_revert_field_restores_source_value():
    packing = sample_packing()
    set_field(packing, "packages[0].net_weight", "80")

    packing, _ = revert_field(packing, "packages[0].net_weight")

    field = packing.packages[0].net_weight
    assert field.working.value == 90
    assert field.working.origin == "source"
    assert field.modified is False


def test_revert_package_only_affects_selected_package():
    packing = sample_packing()
    packing.packages.append(
        Package(
            case_number=mapped_field("C-2"),
            gross_weight=mapped_field(200, "KG"),
            net_weight=mapped_field(180, "KG"),
        )
    )
    set_field(packing, "packages[0].gross_weight", "120")
    set_field(packing, "packages[1].gross_weight", "220")

    packing, changed = revert_package(packing, 0)

    assert changed == 1
    assert packing.packages[0].gross_weight.working.value == 100
    assert packing.packages[1].gross_weight.working.value == 220


def test_revert_all_restores_item_edits_too():
    packing = sample_packing()
    set_field(packing, "packages[0].items[0].quantity", "5")
    set_field(packing, "packages[0].case_number", "C-1A")

    packing, changed = revert_all(packing)

    assert changed == 2
    assert packing.packages[0].items[0].quantity.working.value == 2
    assert packing.packages[0].case_number.working.value == "C-1"
    assert has_modifications(packing) is False


def test_get_field_rejects_non_field_path():
    packing = sample_packing()

    try:
        get_field(packing, "packages[0]")
    except ValueError as exc:
        assert "editable value" in str(exc)
    else:
        raise AssertionError("Expected invalid path to be rejected")
