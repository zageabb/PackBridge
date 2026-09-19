from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse


class OperationsError(ValueError):
    pass


@dataclass(frozen=True)
class RetentionCandidate:
    path: Path
    age_days: int
    kind: str


def sqlite_database_path(database_uri: str) -> Path:
    uri = str(database_uri or "")
    if not uri.startswith("sqlite:///"):
        raise OperationsError("Backup/restore currently supports the PackBridge SQLite deployment.")
    raw = uri[len("sqlite:///"):]
    if not raw:
        raise OperationsError("SQLite database path is missing.")
    return Path(raw).expanduser().resolve()


def _copy_tree(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def create_backup(
    *,
    database_uri: str,
    data_root: Path,
    knowledge_root: Path,
    template_root: Path,
    destination: Path,
) -> Path:
    destination = Path(destination).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    db_path = sqlite_database_path(database_uri)

    with tempfile.TemporaryDirectory(prefix="packbridge-backup-") as temporary:
        stage = Path(temporary)
        (stage / "database").mkdir()

        backup_db = stage / "database" / "packbridge.sqlite3"
        if db_path.is_file():
            source = sqlite3.connect(str(db_path))
            target = sqlite3.connect(str(backup_db))
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()

        _copy_tree(Path(knowledge_root), stage / "knowledge")
        _copy_tree(Path(template_root), stage / "ssd_templates")

        # Operational files are intentionally included; secrets/config are not.
        data_root = Path(data_root)
        if data_root.is_dir():
            _copy_tree(data_root, stage / "data")

        manifest = {
            "format": "packbridge-backup-v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "contains": {
                "database": backup_db.is_file(),
                "knowledge": (stage / "knowledge").is_dir(),
                "ssd_templates": (stage / "ssd_templates").is_dir(),
                "data": (stage / "data").is_dir(),
            },
        }
        (stage / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

        temporary_zip = destination.with_suffix(destination.suffix + ".tmp")
        with zipfile.ZipFile(
            temporary_zip,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            allowZip64=True,
        ) as archive:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(stage).as_posix())
        temporary_zip.replace(destination)

    return destination


def inspect_backup(archive_path: Path) -> dict:
    archive_path = Path(archive_path).expanduser().resolve()
    if not archive_path.is_file():
        raise OperationsError("Backup archive does not exist.")
    try:
        with zipfile.ZipFile(archive_path) as archive:
            names = set(archive.namelist())
            if "manifest.json" not in names:
                raise OperationsError("Backup archive has no PackBridge manifest.")
            manifest = json.loads(archive.read("manifest.json"))
            if manifest.get("format") != "packbridge-backup-v1":
                raise OperationsError("Unsupported PackBridge backup format.")
            return {
                "path": str(archive_path),
                "sha256": _sha256(archive_path),
                "manifest": manifest,
                "entries": len(names),
            }
    except (zipfile.BadZipFile, json.JSONDecodeError) as exc:
        raise OperationsError(f"Invalid PackBridge backup: {exc}") from exc


def restore_backup(
    archive_path: Path,
    *,
    database_uri: str,
    data_root: Path,
    knowledge_root: Path,
    template_root: Path,
) -> dict:
    """Restore a backup. Intended for offline/admin CLI use."""

    inspection = inspect_backup(archive_path)
    db_path = sqlite_database_path(database_uri)

    with tempfile.TemporaryDirectory(prefix="packbridge-restore-") as temporary:
        stage = Path(temporary)
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                target = (stage / member.filename).resolve()
                if stage.resolve() != target and stage.resolve() not in target.parents:
                    raise OperationsError("Backup contains an unsafe path.")
            archive.extractall(stage)

        restored = []
        backup_db = stage / "database" / "packbridge.sqlite3"
        if backup_db.is_file():
            db_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_db, db_path)
            restored.append("database")

        for name, target_root in (
            ("knowledge", Path(knowledge_root)),
            ("ssd_templates", Path(template_root)),
            ("data", Path(data_root)),
        ):
            source = stage / name
            if source.is_dir():
                target_root.mkdir(parents=True, exist_ok=True)
                shutil.copytree(source, target_root, dirs_exist_ok=True)
                restored.append(name)

    return {
        "archive": inspection["path"],
        "sha256": inspection["sha256"],
        "restored": restored,
    }


def retention_candidates(
    data_root: Path,
    *,
    days: int,
    now: datetime | None = None,
) -> list[RetentionCandidate]:
    if days <= 0:
        return []
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    root = Path(data_root)
    candidates: list[RetentionCandidate] = []

    for kind, folder in (
        ("job", root / "jobs"),
        ("ssd-project", root / "ssd-projects"),
    ):
        if not folder.is_dir():
            continue
        for child in folder.iterdir():
            if not child.is_dir():
                continue
            modified = datetime.fromtimestamp(child.stat().st_mtime, tz=timezone.utc)
            if modified < cutoff:
                age = max(0, (now - modified).days)
                candidates.append(
                    RetentionCandidate(path=child, age_days=age, kind=kind)
                )
    return sorted(candidates, key=lambda item: (item.kind, item.path.name))


def apply_retention(
    data_root: Path,
    *,
    days: int,
    dry_run: bool = True,
) -> list[RetentionCandidate]:
    candidates = retention_candidates(data_root, days=days)
    if not dry_run:
        for item in candidates:
            shutil.rmtree(item.path)
    return candidates



def prune_backups(
    backup_root: Path,
    *,
    days: int,
    dry_run: bool = True,
    now: datetime | None = None,
) -> list[Path]:
    if days <= 0:
        return []
    root = Path(backup_root)
    if not root.is_dir():
        return []
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    candidates = []
    for path in root.glob("*.zip"):
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if modified < cutoff:
            candidates.append(path)
    candidates = sorted(candidates)
    if not dry_run:
        for path in candidates:
            path.unlink(missing_ok=True)
    return candidates
