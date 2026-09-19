from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from packbridge.schemas import FieldValue, Package, PackingList
from packbridge.services.mapper import map_packing_list
from packbridge.services.ollama_client import OllamaClient


@dataclass
class CaseMetrics:
    name: str
    elapsed_seconds: float
    package_count_expected: int
    package_count_actual: int
    package_count_correct: bool
    case_set_correct: bool
    field_correct: int
    field_total: int
    item_correct: int
    item_total: int
    null_correct: int
    null_total: int
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _value(field: FieldValue):
    if field.working is not None:
        return field.working.value
    if field.source is not None:
        return field.source.value
    return None


def _package_case(package: Package) -> str:
    value = _value(package.case_number)
    return "" if value is None else str(value)


def _normalise(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, str):
        return " ".join(value.split()).casefold()
    return value


def _field(package: Package, name: str):
    if name == "length":
        return _value(package.dimensions.length)
    if name == "width":
        return _value(package.dimensions.width)
    if name == "height":
        return _value(package.dimensions.height)
    return _value(getattr(package, name))


def _get_path(packing: PackingList, path: str):
    current: Any = packing
    for token in path.split("."):
        if "[" in token and token.endswith("]"):
            name, raw_index = token[:-1].split("[", 1)
            current = getattr(current, name)
            current = current[int(raw_index)]
        else:
            current = getattr(current, token)
    if isinstance(current, FieldValue):
        return _value(current)
    return current


def compare_expected(name: str, packing: PackingList, expected: dict, elapsed: float) -> CaseMetrics:
    errors: list[str] = []
    expected_packages = expected.get("packages") or []
    actual_by_case = {
        _package_case(package): package
        for package in packing.packages
        if _package_case(package)
    }
    expected_cases = {str(item["case_number"]) for item in expected_packages}
    actual_cases = set(actual_by_case)

    field_correct = field_total = 0
    item_correct = item_total = 0

    for expected_package in expected_packages:
        case = str(expected_package["case_number"])
        package = actual_by_case.get(case)
        if package is None:
            errors.append(f"Missing expected package {case}.")
            continue

        for field_name in (
            "gross_weight",
            "net_weight",
            "length",
            "width",
            "height",
            "package_type",
            "internal_reference",
        ):
            if field_name not in expected_package:
                continue
            field_total += 1
            actual = _field(package, field_name)
            expected_value = expected_package[field_name]
            if _normalise(actual) == _normalise(expected_value):
                field_correct += 1
            else:
                errors.append(
                    f"{case}.{field_name}: expected {expected_value!r}, found {actual!r}."
                )

        expected_items = expected_package.get("items") or []
        actual_items = []
        for item in package.items:
            actual_items.append(
                (
                    _normalise(_value(item.item_number)),
                    _normalise(_value(item.description)),
                    _normalise(_value(item.quantity)),
                    _normalise(_value(item.uom)),
                )
            )
        for expected_item in expected_items:
            item_total += 1
            signature = (
                _normalise(expected_item.get("item_number")),
                _normalise(expected_item.get("description")),
                _normalise(expected_item.get("quantity")),
                _normalise(expected_item.get("uom")),
            )
            if signature in actual_items:
                item_correct += 1
            else:
                errors.append(f"{case}: expected item {expected_item!r} was not found.")

    null_total = null_correct = 0
    for path in expected.get("must_be_null") or []:
        null_total += 1
        try:
            value = _get_path(packing, path)
        except (AttributeError, IndexError, ValueError):
            value = "__missing_path__"
        if value in (None, ""):
            null_correct += 1
        else:
            errors.append(f"{path}: expected null/blank, found {value!r}.")

    return CaseMetrics(
        name=name,
        elapsed_seconds=elapsed,
        package_count_expected=len(expected_packages),
        package_count_actual=len(packing.packages),
        package_count_correct=len(packing.packages) == len(expected_packages),
        case_set_correct=actual_cases == expected_cases,
        field_correct=field_correct,
        field_total=field_total,
        item_correct=item_correct,
        item_total=item_total,
        null_correct=null_correct,
        null_total=null_total,
        errors=errors,
    )


def load_golden_cases(root: Path) -> list[tuple[str, str, dict]]:
    root = Path(root)
    cases = []
    for expected_path in sorted(root.glob("*/expected.json")):
        case_dir = expected_path.parent
        source_path = case_dir / "source.txt"
        if not source_path.is_file():
            continue
        cases.append(
            (
                case_dir.name,
                source_path.read_text(encoding="utf-8"),
                json.loads(expected_path.read_text(encoding="utf-8")),
            )
        )
    return cases


def run_benchmark(
    *,
    root: Path,
    base_url: str,
    model: str,
) -> dict:
    benchmark_client = OllamaClient(base_url, model, read_timeout=600, retries=0)
    metrics: list[CaseMetrics] = []

    for name, source, expected in load_golden_cases(root):
        started = time.perf_counter()
        packing = map_packing_list(source, mapper_client=benchmark_client)
        elapsed = time.perf_counter() - started
        metrics.append(compare_expected(name, packing, expected, elapsed))

    aggregate = {
        "model": model,
        "case_count": len(metrics),
        "json_validity_rate": 1.0 if metrics else 0.0,
        "package_grouping_rate": (
            sum(item.package_count_correct and item.case_set_correct for item in metrics) / len(metrics)
            if metrics else 0.0
        ),
        "field_accuracy": (
            sum(item.field_correct for item in metrics)
            / max(1, sum(item.field_total for item in metrics))
        ),
        "item_accuracy": (
            sum(item.item_correct for item in metrics)
            / max(1, sum(item.item_total for item in metrics))
        ),
        "null_preservation_rate": (
            sum(item.null_correct for item in metrics)
            / max(1, sum(item.null_total for item in metrics))
        ),
        "total_seconds": sum(item.elapsed_seconds for item in metrics),
        "average_seconds": (
            sum(item.elapsed_seconds for item in metrics) / len(metrics)
            if metrics else 0.0
        ),
    }
    return {
        "aggregate": aggregate,
        "cases": [item.to_dict() for item in metrics],
    }
