from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KnowledgeHit:
    path: str
    title: str
    text: str
    score: int


def _title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def list_documents(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.md") if path.is_file())


def search(root: Path, query: str, limit: int = 8) -> list[KnowledgeHit]:
    terms = {term for term in re.findall(r"[a-z0-9_\-]{3,}", query.casefold())}
    if not terms:
        return []
    hits = []
    for path in list_documents(root):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        heading = _title(text, path.stem)
        haystack = f"{path.as_posix()} {heading} {text}".casefold()
        score = sum(3 if term in heading.casefold() else 1 for term in terms if term in haystack)
        if score:
            hits.append(
                KnowledgeHit(
                    path=str(path.relative_to(root)),
                    title=heading,
                    text=text,
                    score=score,
                )
            )
    return sorted(hits, key=lambda item: (-item.score, item.path))[:limit]


def context_for(root: Path, query: str, limit: int = 6, max_chars: int = 30_000) -> str:
    hits = search(root, query, limit=limit)
    if not hits:
        return ""
    sections = []
    remaining = max_chars
    for hit in hits:
        text = hit.text[:remaining]
        if not text:
            break
        sections.append(f"<knowledge path={hit.path!r} title={hit.title!r}>\n{text}\n</knowledge>")
        remaining -= len(text)
        if remaining <= 0:
            break
    return "\n\n".join(sections)
