from packbridge.schemas import (
    Dimensions,
    FieldValue,
    OrderContext,
    Package,
    PackingList,
    SourceValue,
    WorkingValue,
)
from packbridge.ssd_schemas import SSDCaseContext, SSDContext
from packbridge.services.aggregation import AggregationInput, build_project_preview


def field(value, unit=None):
    return FieldValue(
        source=SourceValue(value=value, unit=unit),
        working=WorkingValue(value=value, unit=unit, origin="source"),
    )


def packing(case_number, po, position):
    return PackingList(
        order=OrderContext(
            purchase_order=field(po),
            purchase_order_position=field(position),
        ),
        packages=[
            Package(
                case_number=field(case_number),
                dimensions=Dimensions(
                    length=field(100),
                    width=field(100),
                    height=field(100),
                    unit="CM",
                ),
                net_weight=field(10, "KG"),
                gross_weight=field(12, "KG"),
            )
        ],
    )


def complete_context():
    return SSDContext(
        defaults=SSDCaseContext(
            content_description="QBANK",
            equipment_group="011",
            declare_as="System",
            storage_requirement="Outdoor",
            packaging_material="PALLET",
            stackability="Stackable 1 tier",
            dangerous_goods="N",
        )
    )


def test_project_preview_preserves_job_po_and_renumbers_rows():
    preview = build_project_preview(
        [
            AggregationInput(1, "Position 10", packing("CASE-10", "4501", "10")),
            AggregationInput(2, "Position 30", packing("CASE-30", "4501", "30")),
        ],
        complete_context(),
    )

    assert [row.excel_row for row in preview.rows] == [23, 24]
    assert [row.source_job_id for row in preview.rows] == [1, 2]
    assert [row.columns["I"] for row in preview.rows] == ["10", "30"]
    assert [row.columns["S"] for row in preview.rows] == ["CASE-10", "CASE-30"]


def test_project_preview_blocks_case_duplicates_between_jobs():
    preview = build_project_preview(
        [
            AggregationInput(1, "A", packing("CASE-1", "4501", "10")),
            AggregationInput(2, "B", packing("CASE-1", "4501", "30")),
        ],
        complete_context(),
    )

    assert any("CASE-1" in message and "more than one" in message for message in preview.blocking)


def test_project_preview_blocks_more_than_template_capacity():
    inputs = [
        AggregationInput(index, f"Job {index}", packing(f"CASE-{index}", "4501", str(index)))
        for index in range(1, 70)
    ]

    preview = build_project_preview(inputs, complete_context())

    assert len(preview.rows) == 69
    assert preview.rows[-1].excel_row is None
    assert any("supports 68 package rows" in message for message in preview.blocking)
