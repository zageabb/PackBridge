from __future__ import annotations

from packbridge.models import SourceChunk, SourceDocument


def find_source_evidence(job_id: int, locator: str, limit: int = 5) -> list[dict]:
    locator = str(locator or "").strip()
    if not locator:
        return []

    rows = (
        SourceChunk.query.join(SourceDocument)
        .filter(SourceDocument.job_id == job_id)
        .order_by(SourceDocument.id, SourceChunk.position)
        .all()
    )

    def score(row) -> tuple[int, int]:
        candidate = str(row.locator or "").strip()
        left = candidate.casefold()
        right = locator.casefold()
        if left == right:
            rank = 0
        elif left.startswith(right + ",") or right.startswith(left + ","):
            rank = 1
        elif right in left or left in right:
            rank = 2
        else:
            rank = 9
        return rank, row.position

    matches = [row for row in rows if score(row)[0] < 9]
    matches.sort(key=score)

    return [
        {
            "chunk_id": row.id,
            "document_id": row.document_id,
            "document": row.document.original_name,
            "locator": row.locator,
            "position": row.position,
            "text": row.text,
        }
        for row in matches[: max(1, min(limit, 20))]
    ]
