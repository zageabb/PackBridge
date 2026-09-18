from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.getenv("PACKBRIDGE_SECRET_KEY", "packbridge-development-key")
    DEBUG = os.getenv("PACKBRIDGE_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}

    PACKBRIDGE_HOST = os.getenv("PACKBRIDGE_HOST", "0.0.0.0")
    PACKBRIDGE_PORT = int(os.getenv("PACKBRIDGE_PORT", "5078"))

    DATA_ROOT = Path(os.getenv("PACKBRIDGE_DATA_ROOT", BASE_DIR / "data")).resolve()
    KNOWLEDGE_ROOT = Path(os.getenv("PACKBRIDGE_KNOWLEDGE_ROOT", BASE_DIR / "knowledge")).resolve()
    TEMPLATE_ROOT = Path(os.getenv("PACKBRIDGE_TEMPLATE_ROOT", BASE_DIR / "ssd_templates")).resolve()

    OLLAMA_URL = os.getenv("PACKBRIDGE_OLLAMA_URL", "http://192.168.1.249:11434").rstrip("/")
    OLLAMA_MODEL = os.getenv("PACKBRIDGE_OLLAMA_MODEL", "qwen3:14b")

    MAX_CONTENT_LENGTH = int(os.getenv("PACKBRIDGE_MAX_UPLOAD_MB", "100")) * 1024 * 1024
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "PACKBRIDGE_DATABASE_URL",
        f"sqlite:///{(BASE_DIR / 'instance' / 'packbridge.sqlite3').resolve()}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
