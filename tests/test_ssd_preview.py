from packbridge.schemas import (
    Dimensions,
    FieldValue,
    OrderContext,
    Package,
    PackingList,
    SourceValue,
    WorkingValue,
)
from packbridge.ssd_schemas import SSDCaseContext, SSDContext, SSDHeaderContext
from packbridge.services.ssd_preview import build_ssd_preview


def field(value, unit=None):
    return FieldValue(
        source=SourceValue(value=value, unit=unit),
        working=WorkingValue(value=value, unit=unit, origin="source"),
    )


def test_preview_maps_verified_package_fields_and_keeps_context_separate():
    packing = PackingList(
        order=OrderContext(
            purchase_order=field("4500000001"),
            purchase_order_position=field("10"),
        ),
        packages=[
            Package(
                case_number=field("CASE-1"),
                dimensions=Dimensions(
                    length=field(148),
                    width=field(152),
                    height=field(66),
                    unit="CM",
                ),
                net_weight=field(643, "KG"),
                gross_weight=field(830, "KG"),
            )
        ],
    )
    context = SSDContext(
        header=SSDHeaderContext(
            supplier_name="Example Supplier",
            project_name="Project A",
            delivery_location="Site A",
        ),
        defaults=SSDCaseContext(
            content_description="QBANK",
            equipment_group="011",
            declare_as="System",
            storage_requirement="Outdoor",
            packaging_material="PALLET",
            stackability="Stackable 1 tier",
            dangerous_goods="N",
        ),
    )

    preview = build_ssd_preview(packing, context)
    row = preview.rows[0]

    assert row.excel_row == 23
    assert row.columns["C"] == 1
    assert row.columns["D"] == "QBANK"
    assert row.columns["H"] == "4500000001"
    assert row.columns["I"] == "10"
    assert row.columns["J"] == 148
    assert row.columns["K"] == 152
    assert row.columns["L"] == 66
    assert row.columns["N"] == 643
    assert row.columns["O"] == 830
    assert row.columns["S"] == "CASE-1"
    assert round(row.columns["M"], 6) == round(148 * 152 * 66 / 1_000_000, 6)
    assert row.missing_context == []


def test_preview_converts_mm_and_lb_deterministically():
    packing = PackingList(
        packages=[
            Package(
                case_number=field("CASE-2"),
                dimensions=Dimensions(
                    length=field(1480),
                    width=field(1520),
                    height=field(660),
                    unit="MM",
                ),
                net_weight=field(100, "LB"),
                gross_weight=field(120, "LB"),
            )
        ]
    )

    preview = build_ssd_preview(packing)
    row = preview.rows[0]

    assert row.columns["J"] == 148
    assert row.columns["K"] == 152
    assert row.columns["L"] == 66
    assert round(row.columns["N"], 6) == round(100 * 0.45359237, 6)
    assert round(row.columns["O"], 6) == round(120 * 0.45359237, 6)


def test_preview_flags_unverified_ssd_list_value():
    packing = PackingList(
        packages=[
            Package(
                case_number=field("CASE-3"),
                dimensions=Dimensions(
                    length=field(1, "CM"),
                    width=field(1, "CM"),
                    height=field(1, "CM"),
                    unit="CM",
                ),
                net_weight=field(1, "KG"),
                gross_weight=field(2, "KG"),
            )
        ]
    )
    context = SSDContext(defaults=SSDCaseContext(packaging_material="CARDBOARD"))

    preview = build_ssd_preview(packing, context)

    assert any("Packaging Material" in issue for issue in preview.rows[0].issues)



def test_case_override_takes_precedence_over_job_defaults():
    packing = PackingList(
        packages=[
            Package(
                case_number=field("CASE-9"),
                dimensions=Dimensions(
                    length=field(10),
                    width=field(20),
                    height=field(30),
                    unit="CM",
                ),
                net_weight=field(5, "KG"),
                gross_weight=field(6, "KG"),
            )
        ]
    )
    context = SSDContext(
        defaults=SSDCaseContext(
            content_description="QBANK",
            equipment_group="011",
            declare_as="System",
            purchase_order="4500000001",
            purchase_order_position="10",
            storage_requirement="Outdoor",
            packaging_material="PALLET",
            stackability="Stackable 1 tier",
            dangerous_goods="N",
        ),
        case_overrides={
            "CASE-9": SSDCaseContext(
                packaging_material="WOODEN_BOX",
                stackability="Not stackable",
                remarks="Oversize case",
            )
        },
    )

    preview = build_ssd_preview(packing, context)
    row = preview.rows[0]

    assert row.columns["T"] == "WOODEN_BOX"
    assert row.columns["U"] == "Not stackable"
    assert row.columns["X"] == "Oversize case"
    assert row.columns["D"] == "QBANK"
    assert row.origins["T"] == "case_override"
    assert row.origins["D"] == "ssd_context"
