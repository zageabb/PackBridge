from __future__ import annotations

from numbers import Number
from typing import Any

from pydantic import BaseModel

from packbridge.assistant_schemas import AssistantDataQuery
from packbridge.schemas import FieldValue, Package, PackingList


def _value(field: FieldValue):
    if field.working is not None:
        return field.working.value
    if field.source is not None:
        return field.source.value
    return None


def _unit(field: FieldValue, fallback: str | None = None) -> str | None:
    value = None
    if field.working is not None and field.working.unit not in (None, ""):
        value = field.working.unit
    elif field.source is not None and field.source.unit not in (None, ""):
        value = field.source.unit
    elif fallback:
        value = fallback
    if value in (None, ""):
        return None
    return str(value).strip().upper().replace(".", "")


def _number(value) -> float | None:
    if isinstance(value, bool) or value in (None, ""):
        return None
    if isinstance(value, Number):
        return float(value)
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _case_number(package: Package) -> str:
    value = _value(package.case_number)
    return str(value).strip() if value not in (None, "") else "(missing case number)"


def _package_metric(package: Package, field: str) -> tuple[float | None, str | None]:
    if field == "item_count":
        return float(len(package.items)), None
    if field == "gross_weight":
        return _number(_value(package.gross_weight)), _unit(package.gross_weight)
    if field == "net_weight":
        return _number(_value(package.net_weight)), _unit(package.net_weight)
    if field == "length":
        return _number(_value(package.dimensions.length)), _unit(
            package.dimensions.length,
            package.dimensions.unit,
        )
    if field == "width":
        return _number(_value(package.dimensions.width)), _unit(
            package.dimensions.width,
            package.dimensions.unit,
        )
    if field == "height":
        return _number(_value(package.dimensions.height)), _unit(
            package.dimensions.height,
            package.dimensions.unit,
        )
    return None, None


def _compare(left: float, operator: str, right: float) -> bool:
    if operator == "gt":
        return left > right
    if operator == "gte":
        return left >= right
    if operator == "lt":
        return left < right
    if operator == "lte":
        return left <= right
    if operator == "eq":
        return left == right
    return False


def _modified_fields(value: Any, path: str = "") -> list[dict]:
    output: list[dict] = []
    if isinstance(value, FieldValue):
        if value.modified:
            output.append(
                {
                    "path": path,
                    "source_value": value.source.value if value.source else None,
                    "working_value": value.working.value if value.working else None,
                    "unit": _unit(value),
                    "reason": value.working.reason if value.working else None,
                }
            )
        return output
    if isinstance(value, list):
        for index, item in enumerate(value):
            output.extend(_modified_fields(item, f"{path}[{index}]"))
        return output
    if isinstance(value, BaseModel):
        for field_name in value.__class__.model_fields:
            if field_name == "issues":
                continue
            child = f"{path}.{field_name}" if path else field_name
            output.extend(_modified_fields(getattr(value, field_name), child))
    return output


def execute_data_query(packing: PackingList, query: AssistantDataQuery) -> dict:
    operation = query.operation

    if operation == "count_packages":
        return {
            "operation": operation,
            "count": len(packing.packages),
        }

    if operation == "list_modified_fields":
        return {
            "operation": operation,
            "fields": _modified_fields(packing),
        }

    if operation == "list_issues":
        issues = [
            issue.model_dump(mode="json")
            for issue in packing.issues
            if not issue.resolved
            and (query.severity is None or issue.severity == query.severity)
        ]
        return {
            "operation": operation,
            "severity": query.severity,
            "issues": issues,
        }

    if operation == "filter_packages":
        if query.field is None or query.comparator is None or query.value is None:
            return {
                "operation": operation,
                "error": "filter_packages requires field, comparator and value.",
            }

        requested_unit = _unit_text(query.unit)
        matches = []
        skipped_units: set[str] = set()
        missing_cases = []

        for package in packing.packages:
            value, unit = _package_metric(package, query.field)
            if value is None:
                missing_cases.append(_case_number(package))
                continue
            if requested_unit and unit and requested_unit != unit:
                skipped_units.add(unit)
                continue
            if requested_unit and unit is None and query.field != "item_count":
                skipped_units.add("(missing)")
                continue
            if _compare(value, query.comparator, float(query.value)):
                matches.append(
                    {
                        "case_number": _case_number(package),
                        "value": value,
                        "unit": unit,
                    }
                )

        return {
            "operation": operation,
            "field": query.field,
            "comparator": query.comparator,
            "threshold": query.value,
            "unit": requested_unit,
            "matches": matches,
            "skipped_units": sorted(skipped_units),
            "missing_cases": missing_cases,
        }

    if operation == "sum_package_field":
        if query.field not in {"gross_weight", "net_weight", "length", "width", "height", "item_count"}:
            return {
                "operation": operation,
                "error": "sum_package_field requires a supported numeric package field.",
            }

        groups: dict[str, float] = {}
        missing_cases = []
        for package in packing.packages:
            value, unit = _package_metric(package, query.field)
            if value is None:
                missing_cases.append(_case_number(package))
                continue
            key = unit or "(unitless)"
            groups[key] = groups.get(key, 0.0) + value

        return {
            "operation": operation,
            "field": query.field,
            "totals_by_unit": groups,
            "missing_cases": missing_cases,
        }

    return {
        "operation": operation,
        "error": "Unsupported deterministic data query.",
    }


def execute_data_queries(
    packing: PackingList,
    queries: list[AssistantDataQuery],
) -> list[dict]:
    return [execute_data_query(packing, query) for query in queries[:6]]


def _unit_text(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    return str(value).strip().upper().replace(".", "")


def format_data_results(results: list[dict]) -> str:
    sections: list[str] = []

    for result in results:
        if result.get("error"):
            sections.append(str(result["error"]))
            continue

        operation = result.get("operation")
        if operation == "count_packages":
            sections.append(f"Package count: {result['count']}.")
            continue

        if operation == "filter_packages":
            field = str(result.get("field") or "field").replace("_", " ")
            comparator = {
                "gt": ">",
                "gte": ">=",
                "lt": "<",
                "lte": "<=",
                "eq": "=",
            }.get(result.get("comparator"), str(result.get("comparator")))
            unit = f" {result['unit']}" if result.get("unit") else ""
            matches = result.get("matches") or []
            if matches:
                values = ", ".join(
                    f"{item['case_number']} ({item['value']:g}{(' ' + item['unit']) if item.get('unit') else ''})"
                    for item in matches
                )
                sections.append(
                    f"Cases with {field} {comparator} {result['threshold']:g}{unit}: {values}."
                )
            else:
                sections.append(
                    f"No cases have {field} {comparator} {result['threshold']:g}{unit} in the current working data."
                )
            if result.get("skipped_units"):
                sections.append(
                    "Not compared because of different/missing units: "
                    + ", ".join(result["skipped_units"])
                    + "."
                )
            continue

        if operation == "sum_package_field":
            field = str(result.get("field") or "field").replace("_", " ")
            groups = result.get("totals_by_unit") or {}
            if groups:
                values = ", ".join(
                    f"{total:g} {unit if unit != '(unitless)' else ''}".strip()
                    for unit, total in sorted(groups.items())
                )
                sections.append(f"Total {field}: {values}.")
            else:
                sections.append(f"No numeric {field} values are available to total.")
            continue

        if operation == "list_modified_fields":
            fields = result.get("fields") or []
            if not fields:
                sections.append("No working values have been manually changed from the source.")
            else:
                lines = [
                    f"{item['path']}: {item['source_value']!s} -> {item['working_value']!s}"
                    + (f" {item['unit']}" if item.get("unit") else "")
                    for item in fields
                ]
                sections.append("Modified working values:\n" + "\n".join(lines))
            continue

        if operation == "list_issues":
            issues = result.get("issues") or []
            severity = result.get("severity")
            label = f"{severity.lower()} " if severity else ""
            if not issues:
                sections.append(f"No unresolved {label}validation issues are present.")
            else:
                lines = [
                    f"{item['severity']} {item['code']}: {item['message']}"
                    + (f" (Case {item['case_number']})" if item.get("case_number") else "")
                    for item in issues
                ]
                sections.append("Unresolved validation issues:\n" + "\n".join(lines))

    return "\n\n".join(sections).strip()
