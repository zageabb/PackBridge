from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


MappingStatus = Literal["CONFIRMED", "SUPPORTED", "AMBIGUOUS", "MISSING", "INVALID"]
ValueOrigin = Literal[
    "source",
    "user_edit",
    "project_data",
    "default_rule",
    "calculated",
    "assistant_proposal_approved",
]


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: int | None = None
    locator: str | None = None
    raw_text: str | None = None
    status: MappingStatus = "SUPPORTED"


class SourceValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Any = None
    unit: str | None = None
    raw: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class WorkingValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Any = None
    unit: str | None = None
    origin: ValueOrigin = "source"
    modified_by: str | None = None
    reason: str | None = None


class FieldValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: SourceValue | None = None
    working: WorkingValue | None = None
    modified: bool = False
    required: bool = False


class Dimensions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    length: FieldValue = Field(default_factory=FieldValue)
    width: FieldValue = Field(default_factory=FieldValue)
    height: FieldValue = Field(default_factory=FieldValue)
    unit: str | None = None


class PackingItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: FieldValue = Field(default_factory=FieldValue)
    position: FieldValue = Field(default_factory=FieldValue)
    item_number: FieldValue = Field(default_factory=FieldValue)
    description: FieldValue = Field(default_factory=FieldValue)
    serial_number: FieldValue = Field(default_factory=FieldValue)
    quantity: FieldValue = Field(default_factory=FieldValue)
    uom: FieldValue = Field(default_factory=FieldValue)
    length: FieldValue = Field(default_factory=FieldValue)


class Package(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_number: FieldValue = Field(default_factory=lambda: FieldValue(required=True))
    internal_reference: FieldValue = Field(default_factory=FieldValue)
    volume: FieldValue = Field(default_factory=FieldValue)
    dimensions: Dimensions = Field(default_factory=Dimensions)
    gross_weight: FieldValue = Field(default_factory=lambda: FieldValue(required=True))
    net_weight: FieldValue = Field(default_factory=lambda: FieldValue(required=True))
    package_type: FieldValue = Field(default_factory=FieldValue)
    package_description: FieldValue = Field(default_factory=FieldValue)
    status: FieldValue = Field(default_factory=FieldValue)
    packed_by: FieldValue = Field(default_factory=FieldValue)
    pack_date: FieldValue = Field(default_factory=FieldValue)
    items: list[PackingItem] = Field(default_factory=list)


class DocumentIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: str = "packing_list"
    vendor: str | None = None
    document_profile: str | None = None
    document_reference: str | None = None
    document_date: date | None = None


class OrderContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sales_order: FieldValue = Field(default_factory=FieldValue)
    customer_order_number: FieldValue = Field(default_factory=FieldValue)
    position: FieldValue = Field(default_factory=FieldValue)
    project: FieldValue = Field(default_factory=FieldValue)
    customer_project: FieldValue = Field(default_factory=FieldValue)
    purchase_order: FieldValue = Field(default_factory=FieldValue)
    purchase_order_position: FieldValue = Field(default_factory=FieldValue)


class ShipmentContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_type: FieldValue = Field(default_factory=FieldValue)
    description: FieldValue = Field(default_factory=FieldValue)
    country_of_origin: FieldValue = Field(default_factory=FieldValue)
    hs_code: FieldValue = Field(default_factory=FieldValue)
    supplier_name: FieldValue = Field(default_factory=FieldValue)


class MappingIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    severity: Literal["INFO", "WARNING", "BLOCKING"] = "WARNING"
    message: str
    case_number: str | None = None
    field_path: str | None = None
    resolved: bool = False


class PackingList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document: DocumentIdentity = Field(default_factory=DocumentIdentity)
    order: OrderContext = Field(default_factory=OrderContext)
    shipment: ShipmentContext = Field(default_factory=ShipmentContext)
    packages: list[Package] = Field(default_factory=list)
    issues: list[MappingIssue] = Field(default_factory=list)
