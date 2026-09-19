from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import BaseModel

from packbridge.schemas import FieldValue, Package, PackingList
from packbridge.services.working_data import WorkingDataError, get_field


class ReprocessError(ValueError):
    pass


def collect_locators(value: Any) -> set[str]:
    locators: set[str] = set()
    if isinstance(value, FieldValue):
        if value.source:
            for evidence in value.source.evidence:
                if evidence.locator:
                    locators.add(str(evidence.locator))
        return locators
    if isinstance(value, list):
        for item in value:
            locators.update(collect_locators(item))
        return locators
    if isinstance(value, BaseModel):
        for name in value.__class__.model_fields:
            if name == "issues":
                continue
            locators.update(collect_locators(getattr(value, name)))
    return locators


def source_text_for_locators(chunks: list[Any], locators: set[str]) -> str:
    if not locators:
        raise ReprocessError("No retained source evidence locators are available.")

    selected = []
    seen: set[int] = set()
    for locator in sorted(locators):
        for chunk in chunks:
            candidate = str(chunk.locator or "")
            matched = (
                candidate == locator
                or candidate.startswith(locator + ",")
                or locator.startswith(candidate + ",")
            )
            if matched and chunk.id not in seen:
                selected.append(chunk)
                seen.add(chunk.id)

    if not selected:
        raise ReprocessError("No retained source sections matched the selected data.")

    selected.sort(key=lambda item: item.position)
    return "\n\n".join(
        f"[{chunk.locator}]\n{chunk.text}"
        for chunk in selected
    )


def case_number(package: Package) -> str | None:
    field = package.case_number
    value = (
        field.working.value
        if field.working is not None
        else field.source.value if field.source is not None else None
    )
    if value in (None, ""):
        return None
    return str(value).strip()


def find_package(packing: PackingList, expected_case: str | None) -> tuple[Package, int]:
    if expected_case:
        for index, package in enumerate(packing.packages):
            if case_number(package) == expected_case:
                return package, index
    if len(packing.packages) == 1:
        return packing.packages[0], 0
    raise ReprocessError(
        "The reprocessed source did not resolve to the selected package unambiguously."
    )


def remapped_field_path(original_path: str, mapped_package_index: int) -> str:
    parts = original_path.split(".")
    if not parts:
        raise WorkingDataError("Invalid field path.")
    if parts[0].startswith("packages["):
        parts[0] = f"packages[{mapped_package_index}]"
    return ".".join(parts)


def replace_field_from_remap(
    current: PackingList,
    mapped: PackingList,
    path: str,
    *,
    expected_case: str | None = None,
) -> dict:
    target = get_field(current, path)
    mapped_index = 0
    if path.startswith("packages["):
        _, mapped_index = find_package(mapped, expected_case)
    mapped_path = remapped_field_path(path, mapped_index)
    source_field = get_field(mapped, mapped_path)

    before = target.model_dump(mode="json")
    target.source = deepcopy(source_field.source)
    target.working = deepcopy(source_field.working)
    target.modified = False
    return {
        "path": path,
        "mapped_path": mapped_path,
        "before": before,
        "after": target.model_dump(mode="json"),
    }
