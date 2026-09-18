from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProfileMatch:
    path: str
    title: str
    score: int
    matched_indicators: tuple[str, ...]
    total_indicators: int


def _title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def _section_lines(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    collecting = False
    result: list[str] = []
    target = heading.casefold()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            current = stripped[3:].strip().casefold()
            if collecting and current != target:
                break
            collecting = current == target
            continue
        if collecting:
            result.append(line)
    return result


def _recognition_indicators(text: str) -> list[str]:
    values = []
    for line in _section_lines(text, "Typical recognition indicators"):
        match = re.match(r"^\s*[-*]\s+(.+?)\s*$", line)
        if not match:
            continue
        value = match.group(1).strip().strip(chr(96)).strip()
        if value and len(value) <= 160:
            values.append(value)
    return values


def list_profiles(root: Path) -> list[tuple[Path, str, list[str]]]:
    vendor_root = root / "vendors"
    if not vendor_root.exists():
        return []
    profiles = []
    for path in sorted(vendor_root.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        indicators = _recognition_indicators(text)
        if not indicators:
            continue
        profiles.append((path, _title(text, path.stem), indicators))
    return profiles


def match_profile(root: Path, document_text: str, minimum_score: int = 3) -> ProfileMatch | None:
    haystack = " ".join(document_text.casefold().split())
    matches: list[ProfileMatch] = []
    for path, title, indicators in list_profiles(root):
        matched = tuple(
            indicator
            for indicator in indicators
            if " ".join(indicator.casefold().split()) in haystack
        )
        if len(matched) < minimum_score:
            continue
        matches.append(
            ProfileMatch(
                path=str(path.relative_to(root)),
                title=title,
                score=len(matched),
                matched_indicators=matched,
                total_indicators=len(indicators),
            )
        )
    if not matches:
        return None
    return sorted(
        matches,
        key=lambda item: (-item.score, -(item.score / max(item.total_indicators, 1)), item.path),
    )[0]
