from __future__ import annotations

from copy import deepcopy
from typing import Any

from packbridge.schemas import FieldValue, PackingList
from packbridge.ssd_schemas import SSDCaseContext, SSDContext, SSDPreview, SoCsPreviewRow


DECLARE_AS_VALUES = {"System", "Loose Parts"}
STORAGE_VALUES = {"Outdoor", "Outdoor covered", "Indoor", "Indoor heated"}
PACKAGING_VALUES = {
    "PALLET",
    "CARTON_BOX",
    "WOODEN_FRAME",
    "BUNDLE",
    "WOODEN_BOX",
    "DRUM",
    "UNPACKED",
}
STACKABILITY_VALUES = {
    "Stackable 1 tier",
    "Stackable 2 tier",
    "Stackable 3 tier",
    "Not stackable",
}
DANGEROUS_GOODS_VALUES = {"Y", "N"}

CONTEXT_COLUMNS = {
    "D": "content_description",
    "E": "equipment_group",
    "F": "border_crossing_value",
    "G": "declare_as",
    "H": "purchase_order",
    "I": "purchase_order_position",
    "P": "pickup_week_planned",
    "Q": "pickup_week_actual",
    "R": "storage_requirement",
    "T": "packaging_material",
    "U": "stackability",
    "V": "dangerous_goods",
    "W": "item_designation",
    "X": "remarks",
}

EXPECTED_CONTEXT_FIELDS = {
    "content_description",
    "equipment_group",
    "declare_as",
    "purchase_order",
    "purchase_order_position",
    "storage_requirement",
    "packaging_material",
    "stackability",
    "dangerous_goods",
}


def _field_value(field: FieldValue) -> tuple[Any, str | None]:
    if field.working is not None:
        return field.working.value, field.working.unit
    if field.source is not None:
        return field.source.value, field.source.unit
    return None, None


def _number(value: Any) -> float | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _unit(value: str | None) -> str:
    return str(value or "").strip().upper().replace(".", "")


def _dimension_cm(field: FieldValue, fallback_unit: str | None) -> tuple[float | None, str | None]:
    value, field_unit = _field_value(field)
    number = _number(value)
    unit = _unit(field_unit or fallback_unit)
    if number is None:
        return None, None
    if unit in {"CM", ""}:
        return number, "source" if unit == "CM" else "assumed_cm"
    if unit == "MM":
        return number / 10.0, "converted_mm_to_cm"
    if unit in {"M", "METRE", "METER"}:
        return number * 100.0, "converted_m_to_cm"
    if unit in {"IN", "INCH", "INCHES"}:
        return number * 2.54, "converted_in_to_cm"
    return None, f"unsupported_dimension_unit:{unit}"


def _weight_kg(field: FieldValue) -> tuple[float | None, str | None]:
    value, unit_value = _field_value(field)
    number = _number(value)
    unit = _unit(unit_value)
    if number is None:
        return None, None
    if unit in {"KG", ""}:
        return number, "source" if unit == "KG" else "assumed_kg"
    if unit in {"G", "GRAM", "GRAMS"}:
        return number / 1000.0, "converted_g_to_kg"
    if unit in {"LB", "LBS", "POUND", "POUNDS"}:
        return number * 0.45359237, "converted_lb_to_kg"
    return None, f"unsupported_weight_unit:{unit}"


def _text(field: FieldValue) -> str | None:
    value, _ = _field_value(field)
    if value in (None, ""):
        return None
    return str(value).strip()


def _merge_case_context(defaults: SSDCaseContext, override: SSDCaseContext | None) -> SSDCaseContext:
    if override is None:
        return defaults.model_copy(deep=True)
    values = defaults.model_dump()
    for key, value in override.model_dump().items():
        if value not in (None, ""):
            values[key] = value
    return SSDCaseContext.model_validate(values)


def _validate_context(row: SoCsPreviewRow, context: SSDCaseContext) -> None:
    rules = {
        "declare_as": (DECLARE_AS_VALUES, "Declare As"),
        "storage_requirement": (STORAGE_VALUES, "Storage Requirement"),
        "packaging_material": (PACKAGING_VALUES, "Packaging Material"),
        "stackability": (STACKABILITY_VALUES, "Stackability"),
        "dangerous_goods": (DANGEROUS_GOODS_VALUES, "Dangerous Goods"),
    }
    for field_name, (allowed, label) in rules.items():
        value = getattr(context, field_name)
        if value in (None, ""):
            continue
        if str(value) not in allowed:
            row.issues.append(
                f"{label} value {value!r} is outside the verified SSD list."
            )


def build_ssd_preview(packing: PackingList, context: SSDContext | None = None) -> SSDPreview:
    context = context or SSDContext()
    preview = SSDPreview()

    header = context.header
    supplier_from_source = _text(packing.shipment.supplier_name)
    preview.header_cells = {
        "E9": header.currency,
        "E12": header.supplier_name or supplier_from_source,
        "E13": header.pickup_address,
        "E15": header.supplier_contact,
        "E16": header.supplier_phone_email,
        "E17": header.preliminary_final,
        "T6": header.bu_details,
        "T8": header.contact_person_number,
        "T9": header.other_remarks,
        "M10": header.supplier_reference,
        "T12": header.project_name,
        "T13": header.delivery_location,
    }

    for issue in packing.issues:
        text = f"{issue.code}: {issue.message}"
        if issue.severity == "BLOCKING":
            preview.blocking.append(text)
        elif issue.severity == "WARNING" and not issue.resolved:
            preview.warnings.append(text)

    canonical_purchase_order = _text(packing.order.purchase_order)
    canonical_purchase_order_position = _text(packing.order.purchase_order_position)

    for index, package in enumerate(packing.packages):
        case_number = _text(package.case_number)
        override = context.case_overrides.get(case_number or "")
        case_context = _merge_case_context(context.defaults, override)
        if not case_context.purchase_order and canonical_purchase_order:
            case_context.purchase_order = canonical_purchase_order
        if not case_context.purchase_order_position and canonical_purchase_order_position:
            case_context.purchase_order_position = canonical_purchase_order_position

        row = SoCsPreviewRow(
            package_index=index,
            case_number=case_number,
            excel_row=23 + index,
        )
        row.columns["C"] = 1
        row.origins["C"] = "verified_default"

        for column, field_name in CONTEXT_COLUMNS.items():
            value = getattr(case_context, field_name)
            row.columns[column] = value
            row.origins[column] = (
                "case_override"
                if override is not None and getattr(override, field_name) not in (None, "")
                else "ssd_context"
            )
            if field_name in EXPECTED_CONTEXT_FIELDS and value in (None, ""):
                row.missing_context.append(field_name)

        fallback_dimension_unit = package.dimensions.unit
        length, length_origin = _dimension_cm(package.dimensions.length, fallback_dimension_unit)
        width, width_origin = _dimension_cm(package.dimensions.width, fallback_dimension_unit)
        height, height_origin = _dimension_cm(package.dimensions.height, fallback_dimension_unit)
        row.columns.update({"J": length, "K": width, "L": height})
        row.origins.update(
            {
                "J": length_origin or "missing",
                "K": width_origin or "missing",
                "L": height_origin or "missing",
            }
        )
        for label, value, origin in (
            ("Length", length, length_origin),
            ("Width", width, width_origin),
            ("Height", height, height_origin),
        ):
            if value is None and origin and origin.startswith("unsupported_"):
                row.issues.append(f"{label}: {origin.replace('_', ' ')}.")

        if None not in (length, width, height):
            row.columns["M"] = length * width * height / 1_000_000
            row.origins["M"] = "calculated_preview_template_formula"
        else:
            row.columns["M"] = None
            row.origins["M"] = "template_formula"

        net, net_origin = _weight_kg(package.net_weight)
        gross, gross_origin = _weight_kg(package.gross_weight)
        row.columns["N"] = net
        row.columns["O"] = gross
        row.origins["N"] = net_origin or "missing"
        row.origins["O"] = gross_origin or "missing"
        if net is None and net_origin and net_origin.startswith("unsupported_"):
            row.issues.append(net_origin.replace("_", " ") + ".")
        if gross is None and gross_origin and gross_origin.startswith("unsupported_"):
            row.issues.append(gross_origin.replace("_", " ") + ".")

        row.columns["S"] = case_number
        row.origins["S"] = "working_case_number"

        _validate_context(row, case_context)
        preview.rows.append(row)

    missing_headers = [
        cell
        for cell in ("E12", "T12", "T13")
        if preview.header_cells.get(cell) in (None, "")
    ]
    if missing_headers:
        preview.warnings.append(
            "SSD project/header context is incomplete: " + ", ".join(missing_headers) + "."
        )

    missing_rows = sum(bool(row.missing_context) for row in preview.rows)
    if missing_rows:
        preview.warnings.append(
            f"{missing_rows} package row(s) still need SSD-specific project/default values."
        )

    return preview
