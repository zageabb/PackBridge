from __future__ import annotations

import re
from pathlib import Path

import yaml
from flask import current_app

from packbridge.learning_schemas import LearnedProfileDraft
from packbridge.schemas import PackingList

from .prompt_service import render_prompt
from .runtime_settings import client


class ProfileLearningError(RuntimeError):
    pass


def slugify(value: str, fallback: str = "vendor") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").casefold()).strip("-")
    return slug[:80] or fallback


def draft_profile(
    *,
    source_text: str,
    packing: PackingList,
    vendor_hint: str | None = None,
) -> LearnedProfileDraft:
    prompt = render_prompt(
        "profile_learning",
        mapped_data=packing.model_dump_json(indent=2)[:35000],
        source_text=source_text[:40000],
    )
    result = client().generate_json(prompt, LearnedProfileDraft)
    if not result.available:
        raise ProfileLearningError(
            result.warning or result.error_code or "The local model could not draft a document profile."
        )

    draft = result.value
    if vendor_hint and not draft.vendor_name.strip():
        draft.vendor_name = vendor_hint
    return draft


def render_profile_markdown(draft: LearnedProfileDraft) -> str:
    indicators = [
        value.strip()
        for value in draft.recognition_indicators
        if value and value.strip()
    ]
    aliases = [
        alias
        for alias in draft.field_aliases
        if alias.source_term.strip() and alias.canonical_field.strip()
    ]

    lines = [
        f"# {draft.title.strip()}",
        "",
        "## Profile status",
        "",
        "Generated as a PackBridge Learning proposal from a processed source document.",
        "",
        "This profile is mapping guidance only. The source document still passes through the generic local mapper.",
        "",
        "## Typical recognition indicators",
        "",
    ]
    lines.extend(f"- {value}" for value in indicators)
    if not indicators:
        lines.append("- Review and add stable document indicators before approval.")

    lines.extend(
        [
            "",
            "## Observed terminology",
            "",
            "| Source term | Canonical meaning | Note |",
            "|---|---|---|",
        ]
    )
    for alias in aliases:
        note = (alias.note or "").replace("|", "\\|")
        source = alias.source_term.replace("|", "\\|")
        canonical = alias.canonical_field.replace("|", "\\|")
        lines.append(f"| {source} | {canonical} | {note} |")

    rules = {
        "document_profile": {
            "document_type": draft.document_type or "packing_list",
        },
        "field_aliases": {
            alias.source_term: alias.canonical_field
            for alias in aliases
        },
    }
    if draft.continuation_key:
        rules["continuation"] = {"merge_key": draft.continuation_key}

    lines.extend(
        [
            "",
            "## Active structured rules",
            "",
            "~~~packbridge-yaml",
            yaml.safe_dump(
                rules,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            ).rstrip(),
            "~~~",
            "",
            "## Interpretation notes",
            "",
        ]
    )
    if draft.interpretation_notes:
        lines.extend(f"- {note.strip()}" for note in draft.interpretation_notes if note.strip())
    else:
        lines.append("- None proposed.")

    lines.extend(
        [
            "",
            "## Learning governance",
            "",
            "Review the recognition indicators, aliases and structured rules against the source document before approving this profile.",
            "",
        ]
    )
    return "\n".join(lines)


def suggested_profile_path(draft: LearnedProfileDraft, job_id: int, root: Path) -> str:
    vendor_slug = slugify(draft.vendor_name, "unknown-vendor")
    document_slug = slugify(draft.document_type or "packing-list", "packing-list")
    base = Path("vendors") / vendor_slug / f"{document_slug}.md"
    if not (root / base).exists():
        return base.as_posix()

    alternate = Path("vendors") / vendor_slug / f"{document_slug}-layout-{job_id}.md"
    return alternate.as_posix()
