from __future__ import annotations

from numbers import Number

from pydantic import BaseModel

from packbridge.schemas import FieldValue, MappingIssue, PackingList


DIMENSION_UNITS = {"MM", "CM", "M", "METRE", "METER", "IN", "INCH", "INCHES"}
WEIGHT_UNITS = {"G", "GRAM", "GRAMS", "KG", "LB", "LBS", "POUND", "POUNDS"}


def _normalise_unit(value: str | None) -> str:
    return str(value or "").strip().upper().replace(".", "")


def _field_unit(field: FieldValue, fallback: str | None = None) -> str:
    if field.working is not None and field.working.unit not in (None, ""):
        return _normalise_unit(field.working.unit)
    if field.source is not None and field.source.unit not in (None, ""):
        return _normalise_unit(field.source.unit)
    return _normalise_unit(fallback)


def _value(field: FieldValue):
    if field.working is not None:
        return field.working.value
    if field.source is not None:
        return field.source.value
    return None


def _number(field: FieldValue) -> float | None:
    value = _value(field)
    if isinstance(value, bool) or value is None or value == "":
        return None
    if isinstance(value, Number):
        return float(value)
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _case_number(package) -> str | None:
    value = _value(package.case_number)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _field_has_ambiguous_source(field: FieldValue) -> bool:
    if field.working is not None and field.working.origin != "source":
        return False
    if field.source is None:
        return False
    return any(item.status == "AMBIGUOUS" for item in field.source.evidence)


def _ambiguous_mapping_issues(value, path: str = "", case_number: str | None = None) -> list[MappingIssue]:
    issues: list[MappingIssue] = []

    if isinstance(value, FieldValue):
        if _field_has_ambiguous_source(value):
            issues.append(
                MappingIssue(
                    code="MAPPING_AMBIGUOUS",
                    severity="WARNING",
                    message="The source mapper marked this field as ambiguous. Confirm or edit the working value.",
                    case_number=case_number,
                    field_path=path or None,
                )
            )
        return issues

    if isinstance(value, list):
        for index, item in enumerate(value):
            child_path = f"{path}[{index}]" if path else f"[{index}]"
            child_case = case_number
            if hasattr(item, "case_number"):
                child_case = _case_number(item)
            issues.extend(_ambiguous_mapping_issues(item, child_path, child_case))
        return issues

    if isinstance(value, BaseModel):
        local_case = case_number
        if hasattr(value, "case_number"):
            local_case = _case_number(value)
        for field_name in value.__class__.model_fields:
            if field_name == "issues":
                continue
            child_path = f"{path}.{field_name}" if path else field_name
            issues.extend(
                _ambiguous_mapping_issues(
                    getattr(value, field_name),
                    child_path,
                    local_case,
                )
            )
    return issues


def validate_packing_list(packing: PackingList) -> PackingList:
    """Return the canonical document with deterministic issues refreshed.

    The LLM maps business meaning. This function owns checks that normal code can
    perform reliably. Existing mapper notes are not treated as validation facts;
    this routine rebuilds the deterministic issue list every time it is called.
    """

    issues: list[MappingIssue] = []
    seen_cases: set[str] = set()

    if not packing.packages:
        issues.append(
            MappingIssue(
                code="NO_PACKAGES",
                severity="BLOCKING",
                message="No packages/cases were mapped from the source document.",
            )
        )

    for package_index, package in enumerate(packing.packages, start=1):
        case_number = _case_number(package)

        if not case_number:
            issues.append(
                MappingIssue(
                    code="CASE_NUMBER_MISSING",
                    severity="BLOCKING",
                    message=f"Package {package_index} has no case/package identifier.",
                    field_path=f"packages[{package_index - 1}].case_number",
                )
            )
        elif case_number in seen_cases:
            issues.append(
                MappingIssue(
                    code="CASE_NUMBER_DUPLICATE",
                    severity="BLOCKING",
                    message=f"Case {case_number} appears more than once after mapping. Continuation pages should normally be merged.",
                    case_number=case_number,
                    field_path=f"packages[{package_index - 1}].case_number",
                )
            )
        else:
            seen_cases.add(case_number)

        gross = _number(package.gross_weight)
        net = _number(package.net_weight)

        if _value(package.gross_weight) in (None, ""):
            issues.append(
                MappingIssue(
                    code="GROSS_WEIGHT_MISSING",
                    severity="WARNING",
                    message="Gross weight is missing.",
                    case_number=case_number,
                    field_path=f"packages[{package_index - 1}].gross_weight",
                )
            )
        elif gross is None:
            issues.append(
                MappingIssue(
                    code="GROSS_WEIGHT_INVALID",
                    severity="BLOCKING",
                    message="Gross weight is not numeric.",
                    case_number=case_number,
                    field_path=f"packages[{package_index - 1}].gross_weight",
                )
            )

        elif not _field_unit(package.gross_weight):
            issues.append(
                MappingIssue(
                    code="GROSS_WEIGHT_UNIT_MISSING",
                    severity="WARNING",
                    message="Gross weight has no source/working unit.",
                    case_number=case_number,
                    field_path=f"packages[{package_index - 1}].gross_weight",
                )
            )
        elif _field_unit(package.gross_weight) not in WEIGHT_UNITS:
            issues.append(
                MappingIssue(
                    code="GROSS_WEIGHT_UNIT_UNKNOWN",
                    severity="WARNING",
                    message=f"Gross weight unit {_field_unit(package.gross_weight)!r} is not recognised.",
                    case_number=case_number,
                    field_path=f"packages[{package_index - 1}].gross_weight",
                )
            )

        if _value(package.net_weight) in (None, ""):
            issues.append(
                MappingIssue(
                    code="NET_WEIGHT_MISSING",
                    severity="WARNING",
                    message="Net weight is missing.",
                    case_number=case_number,
                    field_path=f"packages[{package_index - 1}].net_weight",
                )
            )
        elif net is None:
            issues.append(
                MappingIssue(
                    code="NET_WEIGHT_INVALID",
                    severity="BLOCKING",
                    message="Net weight is not numeric.",
                    case_number=case_number,
                    field_path=f"packages[{package_index - 1}].net_weight",
                )
            )

        elif not _field_unit(package.net_weight):
            issues.append(
                MappingIssue(
                    code="NET_WEIGHT_UNIT_MISSING",
                    severity="WARNING",
                    message="Net weight has no source/working unit.",
                    case_number=case_number,
                    field_path=f"packages[{package_index - 1}].net_weight",
                )
            )
        elif _field_unit(package.net_weight) not in WEIGHT_UNITS:
            issues.append(
                MappingIssue(
                    code="NET_WEIGHT_UNIT_UNKNOWN",
                    severity="WARNING",
                    message=f"Net weight unit {_field_unit(package.net_weight)!r} is not recognised.",
                    case_number=case_number,
                    field_path=f"packages[{package_index - 1}].net_weight",
                )
            )

        if gross is not None and net is not None and gross < net:
            issues.append(
                MappingIssue(
                    code="GROSS_BELOW_NET",
                    severity="WARNING",
                    message=f"Gross weight ({gross:g}) is lower than net weight ({net:g}).",
                    case_number=case_number,
                    field_path=f"packages[{package_index - 1}].gross_weight",
                )
            )

        dimensions = (
            ("length", package.dimensions.length),
            ("width", package.dimensions.width),
            ("height", package.dimensions.height),
        )
        present_dimensions = [name for name, field in dimensions if _value(field) not in (None, "")]
        if present_dimensions and len(present_dimensions) != 3:
            issues.append(
                MappingIssue(
                    code="DIMENSIONS_INCOMPLETE",
                    severity="WARNING",
                    message="Only part of the L/W/H dimensions were mapped.",
                    case_number=case_number,
                    field_path=f"packages[{package_index - 1}].dimensions",
                )
            )
        for name, dimension_field in dimensions:
            raw_value = _value(dimension_field)
            if raw_value in (None, ""):
                continue
            number = _number(dimension_field)
            field_path = f"packages[{package_index - 1}].dimensions.{name}"
            if number is None or number < 0:
                issues.append(
                    MappingIssue(
                        code="DIMENSION_INVALID",
                        severity="BLOCKING",
                        message=f"{name.title()} must be a non-negative number.",
                        case_number=case_number,
                        field_path=field_path,
                    )
                )
                continue

            unit = _field_unit(dimension_field, package.dimensions.unit)
            if not unit:
                issues.append(
                    MappingIssue(
                        code="DIMENSION_UNIT_MISSING",
                        severity="WARNING",
                        message=f"{name.title()} has no source/working dimension unit.",
                        case_number=case_number,
                        field_path=field_path,
                    )
                )
            elif unit not in DIMENSION_UNITS:
                issues.append(
                    MappingIssue(
                        code="DIMENSION_UNIT_UNKNOWN",
                        severity="WARNING",
                        message=f"{name.title()} unit {unit!r} is not recognised.",
                        case_number=case_number,
                        field_path=field_path,
                    )
                )

        for item_index, item in enumerate(package.items, start=1):
            quantity_value = _value(item.quantity)
            if quantity_value not in (None, "") and _number(item.quantity) is None:
                issues.append(
                    MappingIssue(
                        code="ITEM_QUANTITY_INVALID",
                        severity="WARNING",
                        message=f"Item {item_index} quantity is not numeric.",
                        case_number=case_number,
                        field_path=f"packages[{package_index - 1}].items[{item_index - 1}].quantity",
                    )
                )
            if quantity_value not in (None, "") and _value(item.uom) in (None, ""):
                issues.append(
                    MappingIssue(
                        code="ITEM_UOM_MISSING",
                        severity="WARNING",
                        message=f"Item {item_index} has a quantity but no unit of measure.",
                        case_number=case_number,
                        field_path=f"packages[{package_index - 1}].items[{item_index - 1}].uom",
                    )
                )

    issues.extend(_ambiguous_mapping_issues(packing))
    packing.issues = issues
    return packing
