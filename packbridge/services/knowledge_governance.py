from __future__ import annotations

import difflib
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from packbridge.models import KnowledgeProposalRecord


class KnowledgeGovernanceError(ValueError):
    pass


MAX_KNOWLEDGE_CHARS = 500_000


def validate_knowledge_content(value: str) -> str:
    text = str(value or "")
    if not text.strip():
        raise KnowledgeGovernanceError("Knowledge content cannot be blank.")
    if "\x00" in text:
        raise KnowledgeGovernanceError("Knowledge content contains invalid binary/null characters.")
    if len(text) > MAX_KNOWLEDGE_CHARS:
        raise KnowledgeGovernanceError(
            f"Knowledge content exceeds the {MAX_KNOWLEDGE_CHARS:,}-character safety limit."
        )
    if not any(line.startswith("# ") for line in text.splitlines()):
        raise KnowledgeGovernanceError("Knowledge documents must contain a top-level '# ' heading.")
    return text


def _profile_version(text: str) -> int | None:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.casefold().startswith("version:"):
            continue
        raw = stripped.split(":", 1)[1].strip()
        try:
            return int(raw)
        except ValueError:
            return None
    return None


def _apply_profile_version(current: str, proposed: str, target_path: str) -> str:
    if not str(target_path).replace("\\", "/").startswith("vendors/"):
        return proposed

    next_version = (_profile_version(current) or 0) + 1
    lines = proposed.splitlines()
    version_line = f"Version: {next_version}"

    for index, line in enumerate(lines):
        if line.strip().casefold().startswith("version:"):
            lines[index] = version_line
            return "\n".join(lines) + ("\n" if proposed.endswith("\n") else "")

    heading_index = next(
        (index for index, line in enumerate(lines) if line.startswith("# ")),
        None,
    )
    if heading_index is None:
        return proposed
    lines.insert(heading_index + 1, "")
    lines.insert(heading_index + 2, version_line)
    return "\n".join(lines) + ("\n" if proposed.endswith("\n") else "")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def safe_knowledge_path(root: Path, relative: str, *, must_exist: bool = True) -> Path:
    root = root.resolve()
    relative = str(relative or "").strip().replace("\\", "/")
    if not relative or relative.startswith("/") or ".." in Path(relative).parts:
        raise KnowledgeGovernanceError("Invalid Knowledge document path.")
    if not relative.casefold().endswith(".md"):
        raise KnowledgeGovernanceError("Knowledge documents must be Markdown files.")

    candidate = (root / relative).resolve()
    if root != candidate and root not in candidate.parents:
        raise KnowledgeGovernanceError("Knowledge path is outside the configured Knowledge root.")
    if must_exist and not candidate.is_file():
        raise KnowledgeGovernanceError("Knowledge document does not exist.")
    return candidate


def current_content(root: Path, relative: str) -> tuple[Path, str, str]:
    path = safe_knowledge_path(root, relative, must_exist=True)
    text = path.read_text(encoding="utf-8")
    return path, text, sha256_text(text)


def proposal_diff(root: Path, proposal: KnowledgeProposalRecord) -> str:
    try:
        _, current, _ = current_content(root, proposal.target_path)
    except (OSError, KnowledgeGovernanceError):
        current = ""
    proposed = _apply_profile_version(
        current,
        proposal.proposed_content,
        proposal.target_path,
    )
    diff = difflib.unified_diff(
        current.splitlines(),
        proposed.splitlines(),
        fromfile=proposal.target_path + " (current)",
        tofile=proposal.target_path + " (proposed)",
        lineterm="",
    )
    return "\n".join(diff)


def apply_proposal(
    root: Path,
    proposal: KnowledgeProposalRecord,
    *,
    actor: str = "user",
) -> KnowledgeProposalRecord:
    if proposal.status != "pending":
        raise KnowledgeGovernanceError(f"Proposal is already {proposal.status}.")

    path = safe_knowledge_path(root, proposal.target_path, must_exist=False)
    if path.exists():
        current = path.read_text(encoding="utf-8")
        current_hash = sha256_text(current)
    else:
        current = ""
        current_hash = sha256_text("")

    if current_hash != proposal.base_sha256:
        raise KnowledgeGovernanceError(
            "Knowledge document changed after this proposal was created. Review and create a fresh proposal."
        )

    proposed = validate_knowledge_content(proposal.proposed_content)
    proposed = _apply_profile_version(current, proposed, proposal.target_path)
    proposed = validate_knowledge_content(proposed)

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(proposed, encoding="utf-8")
    temporary.replace(path)

    proposal.status = "applied"
    proposal.decided_by = actor
    proposal.decided_at = datetime.now(timezone.utc)
    proposal.applied_sha256 = sha256_text(proposed)
    return proposal


def reject_proposal(
    proposal: KnowledgeProposalRecord,
    *,
    actor: str = "user",
) -> KnowledgeProposalRecord:
    if proposal.status != "pending":
        raise KnowledgeGovernanceError(f"Proposal is already {proposal.status}.")
    proposal.status = "rejected"
    proposal.decided_by = actor
    proposal.decided_at = datetime.now(timezone.utc)
    return proposal
