from __future__ import annotations

from copy import deepcopy
from typing import Any

from packbridge.schemas import FieldValue, MappingIssue, Package, PackingItem, PackingList


def _value(field: FieldValue) -> Any:
    if field.working is not None:
        return field.working.value
    if field.source is not None:
        return field.source.value
    return None


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _missing(field: FieldValue) -> bool:
    return _value(field) in (None, "")


def _item_key(item: PackingItem) -> tuple[str, ...]:
    return tuple(
        _text(_value(field))
        for field in (
            item.sequence,
            item.position,
            item.item_number,
            item.description,
            item.serial_number,
            item.quantity,
            item.uom,
            item.length,
        )
    )


def _merge_field(
    primary: FieldValue,
    continuation: FieldValue,
    *,
    case_number: str,
    field_path: str,
    issues: list[MappingIssue],
) -> FieldValue:
    if _missing(primary) and not _missing(continuation):
        return continuation.model_copy(deep=True)
    if _missing(continuation):
        return primary

    left = _text(_value(primary))
    right = _text(_value(continuation))
    if left != right:
        issues.append(
            MappingIssue(
                code="CONTINUATION_FIELD_CONFLICT",
                severity="WARNING",
                message=(
                    f"Continuation pages for case {case_number} disagree on "
                    f"{field_path}: {left!r} vs {right!r}. The first mapped value was retained."
                ),
                case_number=case_number,
                field_path=field_path,
            )
        )
    return primary


def _merge_package(
    primary: Package,
    continuation: Package,
    *,
    case_number: str,
    issues: list[MappingIssue],
) -> None:
    simple_fields = (
        "internal_reference",
        "volume",
        "gross_weight",
        "net_weight",
        "package_type",
        "package_description",
        "status",
        "packed_by",
        "pack_date",
    )
    for name in simple_fields:
        setattr(
            primary,
            name,
            _merge_field(
                getattr(primary, name),
                getattr(continuation, name),
                case_number=case_number,
                field_path=f"package.{name}",
                issues=issues,
            ),
        )

    for name in ("length", "width", "height"):
        setattr(
            primary.dimensions,
            name,
            _merge_field(
                getattr(primary.dimensions, name),
                getattr(continuation.dimensions, name),
                case_number=case_number,
                field_path=f"package.dimensions.{name}",
                issues=issues,
            ),
        )
    if not primary.dimensions.unit and continuation.dimensions.unit:
        primary.dimensions.unit = continuation.dimensions.unit
    elif (
        primary.dimensions.unit
        and continuation.dimensions.unit
        and primary.dimensions.unit.casefold() != continuation.dimensions.unit.casefold()
    ):
        issues.append(
            MappingIssue(
                code="CONTINUATION_UNIT_CONFLICT",
                severity="WARNING",
                message=(
                    f"Continuation pages for case {case_number} disagree on the "
                    f"dimension unit: {primary.dimensions.unit!r} vs {continuation.dimensions.unit!r}."
                ),
                case_number=case_number,
                field_path="package.dimensions.unit",
            )
        )

    seen = {_item_key(item) for item in primary.items}
    for item in continuation.items:
        key = _item_key(item)
        if key in seen:
            continue
        primary.items.append(item.model_copy(deep=True))
        seen.add(key)


def merge_continuation_packages(
    packing: PackingList,
) -> tuple[PackingList, list[MappingIssue], int]:
    """Merge mapper outputs that repeat the same non-empty Case Number.

    The generic LLM may map one source page at a time. PackBridge's business rule is
    that Case Number identifies the package, so repeated Case Numbers are treated as
    continuation records. Conflicting package-level values are retained from the first
    occurrence and surfaced as review warnings instead of silently overwritten.
    """

    output = packing.model_copy(deep=True)
    merged: list[Package] = []
    indexes: dict[str, int] = {}
    issues: list[MappingIssue] = []
    merge_count = 0

    for package in output.packages:
        case_number = _text(_value(package.case_number))
        if not case_number:
            merged.append(package)
            continue

        existing_index = indexes.get(case_number)
        if existing_index is None:
            indexes[case_number] = len(merged)
            merged.append(package)
            continue

        _merge_package(
            merged[existing_index],
            package,
            case_number=case_number,
            issues=issues,
        )
        merge_count += 1

    output.packages = merged
    return output, issues, merge_count
