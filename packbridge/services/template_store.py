from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .ssd_template import inspect_template


ALLOWED_TEMPLATE_EXTENSIONS = {".xlsm", ".xlsx"}
ACTIVE_METADATA = "active-template.json"


class TemplateInstallError(ValueError):
    pass


def _metadata_path(root: Path) -> Path:
    return root / ACTIVE_METADATA


def _write_metadata(root: Path, payload: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    path = _metadata_path(root)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def active_template(root: str | Path) -> dict | None:
    root = Path(root)
    metadata_path = _metadata_path(root)
    if not metadata_path.is_file():
        return None
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "available": False,
            "error": "Active SSD template metadata is unreadable.",
        }
    filename = str(metadata.get("filename") or "")
    if not filename:
        return {
            **metadata,
            "available": False,
            "error": "Active SSD template metadata does not name a template.",
        }
    path = (root / filename).resolve()
    if root.resolve() not in path.parents:
        return {
            **metadata,
            "available": False,
            "error": "Active SSD template path is invalid.",
        }
    if not path.is_file():
        return {
            **metadata,
            "available": False,
            "error": "Active SSD template file is missing.",
        }
    inspection = inspect_template(path)
    return {
        **metadata,
        "available": True,
        "path": str(path),
        "inspection": inspection.to_dict(),
    }


def install_template(root: str | Path, upload: FileStorage) -> dict:
    root = Path(root)
    original_name = secure_filename(upload.filename or "") or "ssd-template.xlsm"
    suffix = Path(original_name).suffix.casefold()
    if suffix not in ALLOWED_TEMPLATE_EXTENSIONS:
        raise TemplateInstallError("SSD template must be XLSM or XLSX.")

    root.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        suffix=suffix,
        prefix="packbridge-template-",
        dir=root,
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        upload.stream.seek(0)
        while True:
            chunk = upload.stream.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    upload.stream.seek(0)

    try:
        inspection = inspect_template(temporary)
        if not inspection.compatible:
            details = "; ".join(inspection.errors[:8]) or "Template structure is not compatible."
            raise TemplateInstallError(details)

        versioned_name = f"ssd-template-{inspection.sha256[:12]}{suffix}"
        destination = root / versioned_name
        if not destination.exists():
            os.replace(temporary, destination)
        else:
            temporary.unlink(missing_ok=True)

        metadata = {
            "filename": versioned_name,
            "original_name": original_name,
            "sha256": inspection.sha256,
            "structural_fingerprint": inspection.structural_fingerprint,
            "workbook_type": inspection.workbook_type,
            "has_vba": inspection.has_vba,
            "installed_at": datetime.now(timezone.utc).isoformat(),
        }
        _write_metadata(root, metadata)
        return {
            **metadata,
            "available": True,
            "path": str(destination),
            "inspection": inspect_template(destination).to_dict(),
        }
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
