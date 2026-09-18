from __future__ import annotations

from packbridge.mapper_schemas import MappedDimensions, MappedItem, MappedValue, MapperResult
from packbridge.schemas import (
    Dimensions,
    DocumentIdentity,
    Evidence,
    FieldValue,
    OrderContext,
    Package,
    PackingItem,
    PackingList,
    ShipmentContext,
    SourceValue,
    WorkingValue,
)


def field(mapped: MappedValue, *, required: bool = False) -> FieldValue:
    source = SourceValue(
        value=mapped.value,
        unit=mapped.unit,
        raw=mapped.raw,
        evidence=[
            Evidence(
                locator=mapped.locator,
                raw_text=mapped.raw,
                status=mapped.status,
            )
        ]
        if mapped.locator or mapped.raw
        else [],
    )
    working = WorkingValue(
        value=mapped.value,
        unit=mapped.unit,
        origin="source",
    )
    return FieldValue(source=source, working=working, modified=False, required=required)


def dimensions(mapped: MappedDimensions) -> Dimensions:
    return Dimensions(
        length=field(mapped.length),
        width=field(mapped.width),
        height=field(mapped.height),
        unit=mapped.unit,
    )


def item(mapped: MappedItem) -> PackingItem:
    return PackingItem(
        sequence=field(mapped.sequence),
        position=field(mapped.position),
        item_number=field(mapped.item_number),
        description=field(mapped.description),
        serial_number=field(mapped.serial_number),
        quantity=field(mapped.quantity),
        uom=field(mapped.uom),
        length=field(mapped.length),
    )


def to_packing_list(mapped: MapperResult) -> PackingList:
    packages = []
    for source in mapped.packages:
        packages.append(
            Package(
                case_number=field(source.case_number, required=True),
                internal_reference=field(source.internal_reference),
                volume=field(source.volume),
                dimensions=dimensions(source.dimensions),
                gross_weight=field(source.gross_weight, required=True),
                net_weight=field(source.net_weight, required=True),
                package_type=field(source.package_type),
                package_description=field(source.package_description),
                status=field(source.status),
                packed_by=field(source.packed_by),
                pack_date=field(source.pack_date),
                items=[item(value) for value in source.items],
            )
        )

    return PackingList(
        document=DocumentIdentity(
            document_type=mapped.document_type,
            vendor=mapped.vendor,
            document_profile=mapped.document_profile,
            document_reference=mapped.document_reference,
            document_date=mapped.document_date,
        ),
        order=OrderContext(
            sales_order=field(mapped.order.sales_order),
            customer_order_number=field(mapped.order.customer_order_number),
            position=field(mapped.order.position),
            project=field(mapped.order.project),
            customer_project=field(mapped.order.customer_project),
            purchase_order=field(mapped.order.purchase_order),
            purchase_order_position=field(mapped.order.purchase_order_position),
        ),
        shipment=ShipmentContext(
            product_type=field(mapped.shipment.product_type),
            description=field(mapped.shipment.description),
            country_of_origin=field(mapped.shipment.country_of_origin),
            hs_code=field(mapped.shipment.hs_code),
            supplier_name=field(mapped.shipment.supplier_name),
        ),
        packages=packages,
    )
