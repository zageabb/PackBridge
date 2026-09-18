from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from pydantic import BaseModel

from packbridge.schemas import FieldValue, PackingList, SourceValue, WorkingValue
from packbridge.services.validation import validate_packing_list


_PATH_TOKEN = re.compile(r"([a-z_][a-z0-9_]*)(?:\[(\d+)\])?", re.I)
_ALLOWED_ROOTS = {"order", "shipment", "packages"}


class WorkingDataError(ValueError):
    pass


def load_packing(value: str | dict | PackingList) -> PackingList:
    if isinstance(value, PackingList):
        return value
    if isinstance(value, dict):
        return PackingList.model_validate(value)
    return PackingList.model_validate_json(value)


def dump_packing(packing: PackingList) -> str:
    return packing.model_dump_json()


def get_field(packing: PackingList, path: str) -> FieldValue:
    if not path or any(part in path for part in ("__", "(", ")", "{", "}", ";")):
        raise WorkingDataError("Invalid field path.")

    tokens = path.split(".")
    if not tokens:
        raise WorkingDataError("Invalid field path.")

    first = _PATH_TOKEN.fullmatch(tokens[0])
    if not first or first.group(1) not in _ALLOWED_ROOTS:
        raise WorkingDataError("Field path is outside the editable packing-list model.")

    current: Any = packing
    for raw in tokens:
        match = _PATH_TOKEN.fullmatch(raw)
        if not match:
            raise WorkingDataError("Invalid field path.")
        name, index_text = match.groups()
        if name.startswith("_") or not hasattr(current, name):
            raise WorkingDataError(f"Unknown field path segment: {name}")
        current = getattr(current, name)
        if index_text is not None:
            if not isinstance(current, list):
                raise WorkingDataError(f"{name} is not a list.")
            index = int(index_text)
            if index < 0 or index >= len(current):
                raise WorkingDataError(f"{name}[{index}] is outside the available range.")
            current = current[index]

    if not isinstance(current, FieldValue):
        raise WorkingDataError("The requested path does not point to an editable value.")
    return current


def _source_value(field: FieldValue) -> tuple[Any, str | None]:
    if field.source is None:
        return None, None
    return field.source.value, field.source.unit


def _current_value(field: FieldValue) -> Any:
    if field.working is not None:
        return field.working.value
    if field.source is not None:
        return field.source.value
    return None


_NUMERIC_FIELD_NAMES = {
    "gross_weight",
    "net_weight",
    "volume",
    "length",
    "width",
    "height",
    "quantity",
    "sequence",
}


def _coerce_like(path: str, existing: Any, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
    else:
        stripped = value

    field_name = path.rsplit(".", 1)[-1]
    field_name = field_name.split("[", 1)[0]

    if field_name not in _NUMERIC_FIELD_NAMES:
        return str(stripped)

    if isinstance(existing, bool):
        text = str(stripped).casefold()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
        raise WorkingDataError("Enter a true/false value.")

    if isinstance(existing, int) and not isinstance(existing, bool):
        try:
            return int(str(stripped).replace(",", ""))
        except ValueError as exc:
            raise WorkingDataError("Enter a whole number.") from exc

    try:
        return float(str(stripped).replace(",", ""))
    except ValueError as exc:
        raise WorkingDataError("Enter a numeric value.") from exc


def set_field(
    packing: PackingList,
    path: str,
    value: Any,
    *,
    unit: str | None = None,
    actor: str = "user",
    reason: str | None = None,
) -> tuple[PackingList, dict]:
    field = get_field(packing, path)
    before = {
        "value": _current_value(field),
        "unit": field.working.unit if field.working is not None else (field.source.unit if field.source else None),
        "modified": field.modified,
    }

    source_value, source_unit = _source_value(field)
    existing = _current_value(field)
    coerced = _coerce_like(path, existing if existing is not None else source_value, value)
    working_unit = unit if unit is not None else (
        field.working.unit if field.working is not None else source_unit
    )

    field.working = WorkingValue(
        value=coerced,
        unit=working_unit,
        origin="user_edit",
        modified_by=actor,
        reason=(reason or "").strip() or None,
    )
    field.modified = coerced != source_value or working_unit != source_unit

    if not field.modified:
        field.working.origin = "source"
        field.working.modified_by = None
        field.working.reason = None

    validate_packing_list(packing)
    after = {
        "value": field.working.value if field.working else None,
        "unit": field.working.unit if field.working else None,
        "modified": field.modified,
    }
    return packing, {"path": path, "before": before, "after": after}


def revert_field(packing: PackingList, path: str) -> tuple[PackingList, dict]:
    field = get_field(packing, path)
    before = {
        "value": _current_value(field),
        "unit": field.working.unit if field.working is not None else None,
        "modified": field.modified,
    }
    source = field.source or SourceValue()
    field.working = WorkingValue(value=deepcopy(source.value), unit=source.unit, origin="source")
    field.modified = False
    validate_packing_list(packing)
    return packing, {
        "path": path,
        "before": before,
        "after": {"value": field.working.value, "unit": field.working.unit, "modified": False},
    }


def _revert_model(value: Any) -> int:
    count = 0
    if isinstance(value, FieldValue):
        source = value.source or SourceValue()
        if value.modified:
            count += 1
        value.working = WorkingValue(value=deepcopy(source.value), unit=source.unit, origin="source")
        value.modified = False
        return count
    if isinstance(value, list):
        for item in value:
            count += _revert_model(item)
        return count
    if isinstance(value, BaseModel):
        for field_name in value.model_fields:
            count += _revert_model(getattr(value, field_name))
    return count


def revert_package(packing: PackingList, package_index: int) -> tuple[PackingList, int]:
    if package_index < 0 or package_index >= len(packing.packages):
        raise WorkingDataError("Package index is outside the available range.")
    changed = _revert_model(packing.packages[package_index])
    validate_packing_list(packing)
    return packing, changed


def revert_all(packing: PackingList) -> tuple[PackingList, int]:
    changed = _revert_model(packing)
    validate_packing_list(packing)
    return packing, changed


def issue_counts(packing: PackingList) -> dict[str, int]:
    counts = {"INFO": 0, "WARNING": 0, "BLOCKING": 0}
    for issue in packing.issues:
        counts[issue.severity] = counts.get(issue.severity, 0) + 1
    return counts


def has_modifications(value: Any) -> bool:
    if isinstance(value, FieldValue):
        return bool(value.modified)
    if isinstance(value, list):
        return any(has_modifications(item) for item in value)
    if isinstance(value, BaseModel):
        return any(has_modifications(getattr(value, field_name)) for field_name in value.model_fields)
    return False
