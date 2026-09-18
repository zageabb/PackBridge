from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


JOB_SUBDIRECTORIES = ("source", "rendered", "working", "output")


def ensure_job_directories(base_data_dir: Path, job_id: int) -> Path:
    job_dir = Path(base_data_dir) / "jobs" / str(job_id)
    for directory in JOB_SUBDIRECTORIES:
        (job_dir / directory).mkdir(parents=True, exist_ok=True)
    return job_dir


def save_job_upload(
    base_data_dir: Path,
    job_id: int,
    upload: FileStorage,
) -> tuple[str, str, Path, str, int]:
    job_dir = ensure_job_directories(base_data_dir, job_id)
    original_name = secure_filename(upload.filename or "upload") or "upload"
    extension = Path(original_name).suffix.lower()
    stored_name = f"{uuid.uuid4().hex}{extension}"
    destination = job_dir / "source" / stored_name

    digest = hashlib.sha256()
    size = 0
    upload.stream.seek(0)
    with destination.open("wb") as handle:
        while True:
            chunk = upload.stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
            handle.write(chunk)
    upload.stream.seek(0)
    return original_name, stored_name, destination, digest.hexdigest(), size
