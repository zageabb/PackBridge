from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import yaml


class KnowledgeRuleError(ValueError):
    pass


@dataclass(frozen=True)
class StructuredKnowledgeBlock:
    format: str
    start_line: int
    data: dict[str, Any]


_OPENERS = {
    "~~~packbridge-yaml": ("~~~", "yaml"),
    "~~~packbridge-json": ("~~~", "json"),
}


def extract_structured_blocks(text: str) -> list[StructuredKnowledgeBlock]:
    lines = str(text or "").splitlines()
    blocks: list[StructuredKnowledgeBlock] = []
    index = 0

    while index < len(lines):
        opener = lines[index].strip().casefold()
        definition = _OPENERS.get(opener)
        if definition is None:
            index += 1
            continue

        fence, block_format = definition
        start_line = index + 1
        body: list[str] = []
        index += 1
        while index < len(lines) and lines[index].strip() != fence:
            body.append(lines[index])
            index += 1

        if index >= len(lines):
            raise KnowledgeRuleError(
                f"Unclosed PackBridge {block_format.upper()} block starting at line {start_line}."
            )

        raw = "\n".join(body).strip()
        if not raw:
            raise KnowledgeRuleError(
                f"PackBridge {block_format.upper()} block at line {start_line} is empty."
            )

        try:
            if block_format == "json":
                parsed = json.loads(raw)
            else:
                parsed = yaml.safe_load(raw)
        except (json.JSONDecodeError, yaml.YAMLError) as exc:
            raise KnowledgeRuleError(
                f"Invalid PackBridge {block_format.upper()} block at line {start_line}: {exc}"
            ) from exc

        if not isinstance(parsed, dict):
            raise KnowledgeRuleError(
                f"PackBridge structured block at line {start_line} must contain a mapping/object at its root."
            )

        blocks.append(
            StructuredKnowledgeBlock(
                format=block_format,
                start_line=start_line,
                data=parsed,
            )
        )
        index += 1

    return blocks


def validate_structured_blocks(text: str) -> list[StructuredKnowledgeBlock]:
    blocks = extract_structured_blocks(text)
    for block in blocks:
        _validate_mapping(block.data, path=f"line {block.start_line}")
    return blocks


def _validate_mapping(value: dict[str, Any], *, path: str) -> None:
    if len(value) > 250:
        raise KnowledgeRuleError(f"Structured Knowledge mapping at {path} is too large.")

    for key, child in value.items():
        if not isinstance(key, str) or not key.strip():
            raise KnowledgeRuleError(
                f"Structured Knowledge keys at {path} must be non-empty strings."
            )
        _validate_value(child, path=f"{path}.{key}", depth=1)


def _validate_value(value: Any, *, path: str, depth: int) -> None:
    if depth > 12:
        raise KnowledgeRuleError(
            f"Structured Knowledge nesting exceeds the safety limit at {path}."
        )
    if isinstance(value, dict):
        if len(value) > 500:
            raise KnowledgeRuleError(f"Structured Knowledge mapping at {path} is too large.")
        for key, child in value.items():
            if not isinstance(key, str) or not key.strip():
                raise KnowledgeRuleError(
                    f"Structured Knowledge keys at {path} must be non-empty strings."
                )
            _validate_value(child, path=f"{path}.{key}", depth=depth + 1)
        return
    if isinstance(value, list):
        if len(value) > 1000:
            raise KnowledgeRuleError(f"Structured Knowledge list at {path} is too large.")
        for index, child in enumerate(value):
            _validate_value(child, path=f"{path}[{index}]", depth=depth + 1)
        return
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    raise KnowledgeRuleError(
        f"Structured Knowledge value at {path} uses unsupported type {type(value).__name__}."
    )


def merged_structured_rules(text: str) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for block in validate_structured_blocks(text):
        merged = _deep_merge(merged, block.data)
    return merged


def _deep_merge(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    output = dict(left)
    for key, value in right.items():
        if (
            key in output
            and isinstance(output[key], dict)
            and isinstance(value, dict)
        ):
            output[key] = _deep_merge(output[key], value)
        else:
            output[key] = value
    return output
