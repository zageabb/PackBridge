from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SSDHeaderContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: str | None = None
    supplier_name: str | None = None
    pickup_address: str | None = None
    supplier_contact: str | None = None
    preliminary_final: str | None = None
    bu_details: str | None = None
    project_name: str | None = None
    delivery_location: str | None = None
    contact_person_number: str | None = None
    other_remarks: str | None = None
    supplier_reference: str | None = None


class SSDCaseContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_description: str | None = None
    equipment_group: str | None = None
    border_crossing_value: float | None = None
    declare_as: str | None = None
    purchase_order: str | None = None
    purchase_order_position: str | None = None
    pickup_week_planned: str | None = None
    pickup_week_actual: str | None = None
    storage_requirement: str | None = None
    packaging_material: str | None = None
    stackability: str | None = None
    dangerous_goods: str | None = None
    item_designation: str | None = None
    remarks: str | None = None


class SSDContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    header: SSDHeaderContext = Field(default_factory=SSDHeaderContext)
    defaults: SSDCaseContext = Field(default_factory=SSDCaseContext)
    case_overrides: dict[str, SSDCaseContext] = Field(default_factory=dict)


class SoCsPreviewRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package_index: int
    case_number: str | None = None
    excel_row: int | None = None
    columns: dict[str, Any] = Field(default_factory=dict)
    origins: dict[str, str] = Field(default_factory=dict)
    missing_context: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class SSDPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    header_cells: dict[str, Any] = Field(default_factory=dict)
    rows: list[SoCsPreviewRow] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocking: list[str] = Field(default_factory=list)
