from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Callable

from flask import current_app

from packbridge.mapper_schemas import (
    MappedDimensions,
    MappedItem,
    MappedPackage,
    MappedValue,
    MapperResult,
)
from packbridge.schemas import MappingIssue, PackingList

from .knowledge import context_for
from .normalise import to_packing_list
from .prompt_service import render_prompt
from .postprocess import merge_continuation_packages
from .runtime_settings import client
from .validation import validate_packing_list


MAX_MAPPING_TEXT = 120_000
SEGMENT_TARGET_CHARS = 45_000
MAX_MAPPING_SEGMENTS = 24


class MappingError(RuntimeError):
    pass


def split_mapping_segments(
    document_text: str,
    *,
    target_chars: int = SEGMENT_TARGET_CHARS,
    max_segments: int = MAX_MAPPING_SEGMENTS,
) -> list[str]:
    """Split large extracted documents on retained section/page boundaries.

    A modest local model performs more consistently on bounded segments. Sections are
    kept whole where possible so page/table locators remain useful as evidence.
    """

    text = str(document_text or "").strip()
    if not text:
        return []
    if len(text) <= target_chars:
        return [text]

    sections = [
        section.strip()
        for section in re.split(r"(?=^\[[^\]\n]{1,180}\]\n)", text, flags=re.MULTILINE)
        if section.strip()
    ]
    if len(sections) <= 1:
        # Fallback for sources without our locator wrapper.
        overlap = min(1500, max(0, target_chars // 12))
        step = max(1, target_chars - overlap)
        segments = [text[start : start + target_chars] for start in range(0, len(text), step)]
        if len(segments) > max_segments:
            raise MappingError(
                f"Document requires {len(segments)} mapping segments, exceeding the safety limit of {max_segments}."
            )
        return segments

    segments: list[str] = []
    current: list[str] = []
    current_chars = 0

    for section in sections:
        addition = len(section) + (2 if current else 0)
        if current and current_chars + addition > target_chars:
            segments.append("\n\n".join(current))
            current = []
            current_chars = 0

        # Preserve an unusually large page/section rather than cutting its evidence locator.
        current.append(section)
        current_chars += len(section) + (2 if len(current) > 1 else 0)

    if current:
        segments.append("\n\n".join(current))

    if len(segments) > max_segments:
        raise MappingError(
            f"Document requires {len(segments)} mapping segments, exceeding the safety limit of {max_segments}."
        )
    return segments


_STATUS_RANK = {
    "MISSING": 0,
    "AMBIGUOUS": 1,
    "SUPPORTED": 2,
    "CONFIRMED": 3,
}


def _is_present(value: MappedValue) -> bool:
    return value.value not in (None, "")


def _normalised_value(value) -> str:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    except TypeError:
        return str(value)


def _merge_value(
    left: MappedValue,
    right: MappedValue,
    *,
    field_label: str,
    conflicts: list[str],
) -> MappedValue:
    if not _is_present(left):
        return deepcopy(right)
    if not _is_present(right):
        return deepcopy(left)

    if _normalised_value(left.value) == _normalised_value(right.value):
        if _STATUS_RANK.get(right.status, 0) > _STATUS_RANK.get(left.status, 0):
            return deepcopy(right)
        return deepcopy(left)

    left_rank = _STATUS_RANK.get(left.status, 0)
    right_rank = _STATUS_RANK.get(right.status, 0)
    if right_rank > left_rank:
        chosen = deepcopy(right)
    else:
        chosen = deepcopy(left)

    conflicts.append(
        f"{field_label} had conflicting segment values {left.value!r} and {right.value!r}; "
        f"kept {chosen.value!r} ({chosen.status})."
    )
    return chosen


def _item_identity(item: MappedItem) -> tuple[str, ...]:
    values = (
        item.sequence.value,
        item.position.value,
        item.item_number.value,
        item.description.value,
        item.serial_number.value,
        item.quantity.value,
        item.uom.value,
        item.length.value,
    )
    return tuple(_normalised_value(value) for value in values)


def _merge_dimensions(
    left: MappedDimensions,
    right: MappedDimensions,
    *,
    label: str,
    conflicts: list[str],
) -> MappedDimensions:
    return MappedDimensions(
        length=_merge_value(left.length, right.length, field_label=f"{label}.length", conflicts=conflicts),
        width=_merge_value(left.width, right.width, field_label=f"{label}.width", conflicts=conflicts),
        height=_merge_value(left.height, right.height, field_label=f"{label}.height", conflicts=conflicts),
        unit=left.unit or right.unit,
    )


def _merge_package(
    left: MappedPackage,
    right: MappedPackage,
    *,
    case_key: str,
    conflicts: list[str],
) -> MappedPackage:
    merged = deepcopy(left)
    simple_fields = (
        "case_number",
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
            merged,
            name,
            _merge_value(
                getattr(left, name),
                getattr(right, name),
                field_label=f"case {case_key}.{name}",
                conflicts=conflicts,
            ),
        )
    merged.dimensions = _merge_dimensions(
        left.dimensions,
        right.dimensions,
        label=f"case {case_key}.dimensions",
        conflicts=conflicts,
    )

    seen = {_item_identity(item) for item in merged.items}
    for item in right.items:
        identity = _item_identity(item)
        if identity not in seen:
            merged.items.append(deepcopy(item))
            seen.add(identity)
    return merged


def merge_mapper_results(results: list[MapperResult]) -> tuple[MapperResult, list[str]]:
    if not results:
        return MapperResult(), []
    if len(results) == 1:
        return deepcopy(results[0]), []

    merged = deepcopy(results[0])
    conflicts: list[str] = []

    for result in results[1:]:
        if not merged.vendor and result.vendor:
            merged.vendor = result.vendor
        if not merged.document_profile and result.document_profile:
            merged.document_profile = result.document_profile
        if not merged.document_reference and result.document_reference:
            merged.document_reference = result.document_reference
        if not merged.document_date and result.document_date:
            merged.document_date = result.document_date
        if merged.document_type == "packing_list" and result.document_type:
            merged.document_type = result.document_type

        for field_name in merged.order.__class__.model_fields:
            setattr(
                merged.order,
                field_name,
                _merge_value(
                    getattr(merged.order, field_name),
                    getattr(result.order, field_name),
                    field_label=f"order.{field_name}",
                    conflicts=conflicts,
                ),
            )
        for field_name in merged.shipment.__class__.model_fields:
            setattr(
                merged.shipment,
                field_name,
                _merge_value(
                    getattr(merged.shipment, field_name),
                    getattr(result.shipment, field_name),
                    field_label=f"shipment.{field_name}",
                    conflicts=conflicts,
                ),
            )

        package_indexes: dict[str, int] = {}
        for index, package in enumerate(merged.packages):
            if _is_present(package.case_number):
                package_indexes[str(package.case_number.value).strip()] = index

        for package in result.packages:
            case_value = str(package.case_number.value).strip() if _is_present(package.case_number) else ""
            if case_value and case_value in package_indexes:
                index = package_indexes[case_value]
                merged.packages[index] = _merge_package(
                    merged.packages[index],
                    package,
                    case_key=case_value,
                    conflicts=conflicts,
                )
            else:
                merged.packages.append(deepcopy(package))
                if case_value:
                    package_indexes[case_value] = len(merged.packages) - 1

        merged.notes.extend(note for note in result.notes if note not in merged.notes)

    return merged, conflicts


def _map_segment(
    segment: str,
    *,
    profile_hint: str,
    knowledge: str,
    segment_number: int,
    segment_count: int,
) -> MapperResult:
    segment_hint = profile_hint or "No profile selected. Use generic packing-list mapping."
    if segment_count > 1:
        segment_hint += (
            f" This is segment {segment_number} of {segment_count}. "
            "Extract only records/evidence present in this segment. "
            "The application will merge repeated case identifiers across segments."
        )

    prompt = render_prompt(
        "packing_list_mapping",
        profile_hint=segment_hint,
        knowledge_context=knowledge or "No vendor-specific knowledge matched.",
        document_text=segment,
    )

    result = client().generate_json(prompt, MapperResult)
    if not result.available:
        raise MappingError(
            f"Local mapper failed on segment {segment_number}/{segment_count}: "
            f"{result.warning or result.error_code or 'unknown error'}"
        )
    return result.value


def map_packing_list(
    document_text: str,
    profile_hint: str = "",
    *,
    profile_path: str | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> PackingList:
    knowledge_root = Path(current_app.config["KNOWLEDGE_ROOT"])
    query = "packing list package case gross net dimensions items UOM"
    if profile_hint:
        query += " " + profile_hint
    knowledge = context_for(knowledge_root, query, limit=8, max_chars=35_000)

    if profile_path:
        candidate = (knowledge_root / profile_path).resolve()
        if (
            candidate.is_file()
            and (candidate == knowledge_root or knowledge_root in candidate.parents)
            and candidate.suffix.casefold() == ".md"
        ):
            profile_text = candidate.read_text(encoding="utf-8")
            explicit_profile = (
                f"<active_document_profile path={profile_path!r}>\n"
                f"{profile_text[:30000]}\n"
                "</active_document_profile>"
            )
            if profile_text[:500] not in knowledge:
                knowledge = explicit_profile + "\n\n" + knowledge

    # Keep the original single-call path for ordinary documents. Larger documents
    # are segmented rather than silently truncated.
    target = min(MAX_MAPPING_TEXT, SEGMENT_TARGET_CHARS)
    segments = split_mapping_segments(document_text, target_chars=target)
    mapped_segments = []
    segment_count = len(segments)
    for index, segment in enumerate(segments, start=1):
        if progress_callback is not None:
            progress_callback("mapping", index - 1, segment_count)
        mapped_segments.append(
            _map_segment(
                segment,
                profile_hint=profile_hint,
                knowledge=knowledge,
                segment_number=index,
                segment_count=segment_count,
            )
        )
        if progress_callback is not None:
            progress_callback("mapping", index, segment_count)

    if progress_callback is not None:
        progress_callback("merging", segment_count, segment_count)
    merged_result, merge_conflicts = merge_mapper_results(mapped_segments)
    packing = to_packing_list(merged_result)
    packing, continuation_issues, _ = merge_continuation_packages(packing)
    if progress_callback is not None:
        progress_callback("validating", segment_count, segment_count)
    packing = validate_packing_list(packing)
    packing.issues.extend(continuation_issues)
    packing.issues.extend(
        MappingIssue(
            code="CHUNK_MERGE_CONFLICT",
            severity="WARNING",
            message=message,
        )
        for message in merge_conflicts
    )
    return packing
