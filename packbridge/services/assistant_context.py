from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from packbridge.models import Job, SourceChunk, SourceDocument
from packbridge.schemas import FieldValue, PackingList


MAX_SOURCE_EXCERPTS = 8
MAX_SOURCE_TEXT = 3500


def _working_value(field: FieldValue) -> Any:
    if field.working is not None:
        return field.working.value
    if field.source is not None:
        return field.source.value
    return None


def _field_snapshot(field: FieldValue) -> dict:
    evidence = []
    if field.source:
        evidence = [
            {
                "locator": item.locator,
                "raw_text": item.raw_text,
                "status": item.status,
            }
            for item in field.source.evidence[:3]
        ]
    return {
        "source_value": field.source.value if field.source else None,
        "source_unit": field.source.unit if field.source else None,
        "working_value": field.working.value if field.working else None,
        "working_unit": field.working.unit if field.working else None,
        "working_origin": field.working.origin if field.working else None,
        "modified": field.modified,
        "evidence": evidence,
    }


def _collect_locators(value: Any, result: set[str]) -> None:
    if isinstance(value, FieldValue):
        if value.source:
            for item in value.source.evidence:
                if item.locator:
                    result.add(str(item.locator))
        return
    if isinstance(value, list):
        for item in value:
            _collect_locators(item, result)
        return
    if isinstance(value, BaseModel):
        for field_name in value.__class__.model_fields:
            _collect_locators(getattr(value, field_name), result)


def _matching_source_chunks(job_id: int, locators: set[str]) -> list[dict]:
    query = (
        SourceChunk.query.join(SourceDocument)
        .filter(SourceDocument.job_id == job_id)
        .order_by(SourceDocument.id, SourceChunk.position)
    )
    rows = query.all()
    if not rows:
        return []

    selected = []
    seen_ids: set[int] = set()

    def add(row):
        if row.id in seen_ids or len(selected) >= MAX_SOURCE_EXCERPTS:
            return
        seen_ids.add(row.id)
        selected.append(
            {
                "chunk_id": row.id,
                "document": row.document.original_name,
                "locator": row.locator,
                "text": row.text[:MAX_SOURCE_TEXT],
            }
        )

    for locator in sorted(locators):
        for row in rows:
            candidate = str(row.locator or "")
            if candidate == locator:
                add(row)
        for row in rows:
            candidate = str(row.locator or "")
            if candidate.startswith(locator + ",") or locator.startswith(candidate + ","):
                add(row)
        for row in rows:
            candidate = str(row.locator or "")
            if locator.casefold() in candidate.casefold() or candidate.casefold() in locator.casefold():
                add(row)
        if len(selected) >= MAX_SOURCE_EXCERPTS:
            break

    if not selected:
        for row in rows[: min(3, MAX_SOURCE_EXCERPTS)]:
            add(row)

    return selected


def _selected_package(packing: PackingList, selected_case: str | None):
    if not selected_case:
        return None, None
    for index, package in enumerate(packing.packages):
        value = _working_value(package.case_number)
        if value is not None and str(value) == str(selected_case):
            return package, index
    return None, None


def build_assistant_context(
    job: Job,
    packing: PackingList | None,
    selected_case: str | None = None,
) -> dict:
    context: dict[str, Any] = {
        "job": {
            "id": job.id,
            "status": job.status,
            "vendor": job.vendor,
            "document_profile": job.document_profile,
            "sales_order": job.sales_order,
        },
        "selected_case": selected_case,
    }

    if packing is None:
        context["source_evidence"] = _matching_source_chunks(job.id, set())
        return context

    package, package_index = _selected_package(packing, selected_case)

    context["order"] = {
        name: _field_snapshot(getattr(packing.order, name))
        for name in packing.order.__class__.model_fields
    }
    context["shipment"] = {
        name: _field_snapshot(getattr(packing.shipment, name))
        for name in packing.shipment.__class__.model_fields
    }
    context["package_summary"] = [
        {
            "index": index,
            "case_number": _working_value(item.case_number),
            "gross_weight": _working_value(item.gross_weight),
            "gross_weight_unit": item.gross_weight.working.unit if item.gross_weight.working else None,
            "net_weight": _working_value(item.net_weight),
            "net_weight_unit": item.net_weight.working.unit if item.net_weight.working else None,
            "length": _working_value(item.dimensions.length),
            "width": _working_value(item.dimensions.width),
            "height": _working_value(item.dimensions.height),
            "dimension_unit": item.dimensions.unit,
            "item_count": len(item.items),
        }
        for index, item in enumerate(packing.packages)
    ]
    context["issues"] = [issue.model_dump(mode="json") for issue in packing.issues]

    locators: set[str] = set()
    _collect_locators(packing.order, locators)
    _collect_locators(packing.shipment, locators)

    if package is not None:
        context["selected_package_index"] = package_index
        context["selected_package"] = package.model_dump(mode="json")
        _collect_locators(package, locators)

    context["source_evidence"] = _matching_source_chunks(job.id, locators)
    return context
