from __future__ import annotations

from pathlib import Path

from flask import Blueprint, abort, current_app, render_template, request

from packbridge.services.knowledge import list_documents, search

bp = Blueprint("knowledge", __name__, url_prefix="/knowledge")


def _safe_document(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if root != candidate and root not in candidate.parents:
        abort(400)
    if not candidate.is_file() or candidate.suffix.casefold() != ".md":
        abort(404)
    return candidate


@bp.get("/")
def index():
    root = Path(current_app.config["KNOWLEDGE_ROOT"]).resolve()
    query = request.args.get("q", "").strip()
    selected_path = request.args.get("path", "").strip()

    if query:
        hits = search(root, query, limit=50)
        documents = [
            {
                "path": hit.path,
                "title": hit.title,
                "score": hit.score,
            }
            for hit in hits
        ]
    else:
        documents = []
        for path in list_documents(root):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            title = path.stem
            for line in text.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            documents.append(
                {
                    "path": str(path.relative_to(root)),
                    "title": title,
                    "score": None,
                }
            )

    selected = None
    if selected_path:
        path = _safe_document(root, selected_path)
        selected = {
            "path": str(path.relative_to(root)),
            "content": path.read_text(encoding="utf-8"),
        }
    elif documents:
        path = _safe_document(root, documents[0]["path"])
        selected = {
            "path": str(path.relative_to(root)),
            "content": path.read_text(encoding="utf-8"),
        }

    return render_template(
        "knowledge.html",
        documents=documents,
        selected=selected,
        query=query,
    )
