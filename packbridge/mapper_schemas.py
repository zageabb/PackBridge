from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MappedValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def normalise_shorthand(cls, value):
        # Faster/provider-backed models sometimes return the mapped scalar
        # directly even when given the full JSON schema. Preserve strict
        # canonical output by normalising that shorthand at the boundary.
        if value is None:
            return {"value": None, "status": "MISSING"}
        if not isinstance(value, dict):
            return {"value": value, "status": "SUPPORTED"}

        known = {"value", "unit", "raw", "locator", "status"}
        if known.intersection(value):
            cleaned = {key: value[key] for key in known if key in value}
            status = cleaned.get("status")
            if isinstance(status, str):
                cleaned["status"] = status.strip().upper()
            if "status" not in cleaned:
                cleaned["status"] = (
                    "MISSING" if cleaned.get("value") in (None, "") else "SUPPORTED"
                )
            return cleaned

        # Common compact provider forms. Do not retain unsupported metadata.
        for alias in ("text", "content", "mapped_value", "result"):
            if alias in value and len(value) <= 4:
                return {
                    "value": value.get(alias),
                    "unit": value.get("unit"),
                    "raw": value.get("raw"),
                    "locator": value.get("locator"),
                    "status": "SUPPORTED",
                }
        return value

    value: Any = None
    unit: str | None = None
    raw: str | None = None
    locator: str | None = None
    status: Literal["CONFIRMED", "SUPPORTED", "AMBIGUOUS", "MISSING"] = "MISSING"


class MappedDimensions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    length: MappedValue = Field(default_factory=MappedValue)
    width: MappedValue = Field(default_factory=MappedValue)
    height: MappedValue = Field(default_factory=MappedValue)
    unit: str | None = None


class MappedItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: MappedValue = Field(default_factory=MappedValue)
    position: MappedValue = Field(default_factory=MappedValue)
    item_number: MappedValue = Field(default_factory=MappedValue)
    description: MappedValue = Field(default_factory=MappedValue)
    serial_number: MappedValue = Field(default_factory=MappedValue)
    quantity: MappedValue = Field(default_factory=MappedValue)
    uom: MappedValue = Field(default_factory=MappedValue)
    length: MappedValue = Field(default_factory=MappedValue)


class MappedPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_number: MappedValue = Field(default_factory=MappedValue)
    internal_reference: MappedValue = Field(default_factory=MappedValue)
    volume: MappedValue = Field(default_factory=MappedValue)
    dimensions: MappedDimensions = Field(default_factory=MappedDimensions)
    gross_weight: MappedValue = Field(default_factory=MappedValue)
    net_weight: MappedValue = Field(default_factory=MappedValue)
    package_type: MappedValue = Field(default_factory=MappedValue)
    package_description: MappedValue = Field(default_factory=MappedValue)
    status: MappedValue = Field(default_factory=MappedValue)
    packed_by: MappedValue = Field(default_factory=MappedValue)
    pack_date: MappedValue = Field(default_factory=MappedValue)
    items: list[MappedItem] = Field(default_factory=list)


class MappedOrder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sales_order: MappedValue = Field(default_factory=MappedValue)
    customer_order_number: MappedValue = Field(default_factory=MappedValue)
    position: MappedValue = Field(default_factory=MappedValue)
    project: MappedValue = Field(default_factory=MappedValue)
    customer_project: MappedValue = Field(default_factory=MappedValue)
    purchase_order: MappedValue = Field(default_factory=MappedValue)
    purchase_order_position: MappedValue = Field(default_factory=MappedValue)


class MappedShipment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_type: MappedValue = Field(default_factory=MappedValue)
    description: MappedValue = Field(default_factory=MappedValue)
    country_of_origin: MappedValue = Field(default_factory=MappedValue)
    hs_code: MappedValue = Field(default_factory=MappedValue)
    supplier_name: MappedValue = Field(default_factory=MappedValue)


class MapperResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: str = "packing_list"
    vendor: str | None = None
    document_profile: str | None = None
    document_reference: str | None = None
    document_date: date | None = None
    order: MappedOrder = Field(default_factory=MappedOrder)
    shipment: MappedShipment = Field(default_factory=MappedShipment)
    packages: list[MappedPackage] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
