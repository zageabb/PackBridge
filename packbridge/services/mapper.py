from __future__ import annotations

from pathlib import Path

from flask import current_app

from packbridge.mapper_schemas import MapperResult
from packbridge.schemas import PackingList

from .knowledge import context_for
from .normalise import to_packing_list
from .prompt_service import render_prompt
from .runtime_settings import client
from .validation import validate_packing_list


MAX_MAPPING_TEXT = 120_000


class MappingError(RuntimeError):
    pass


def map_packing_list(document_text: str, profile_hint: str = "") -> PackingList:
    knowledge_root = Path(current_app.config["KNOWLEDGE_ROOT"])
    query = "packing list package case gross net dimensions items UOM"
    if profile_hint:
        query += " " + profile_hint
    knowledge = context_for(knowledge_root, query, limit=8, max_chars=35_000)

    prompt = render_prompt(
        "packing_list_mapping",
        profile_hint=profile_hint or "No profile selected. Use generic packing-list mapping.",
        knowledge_context=knowledge or "No vendor-specific knowledge matched.",
        document_text=document_text[:MAX_MAPPING_TEXT],
    )

    result = client().generate_json(prompt, MapperResult)
    if not result.available:
        raise MappingError(result.warning or result.error_code or "Local mapper failed.")

    packing = to_packing_list(result.value)
    return validate_packing_list(packing)
