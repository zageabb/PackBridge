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
    PACKBRIDGE_PORT = int(os.getenv("PACKBRIDGE_PORT", "5085"))

    DATA_ROOT = Path(os.getenv("PACKBRIDGE_DATA_ROOT", BASE_DIR / "data")).resolve()
    KNOWLEDGE_ROOT = Path(os.getenv("PACKBRIDGE_KNOWLEDGE_ROOT", BASE_DIR / "knowledge")).resolve()
    TEMPLATE_ROOT = Path(os.getenv("PACKBRIDGE_TEMPLATE_ROOT", BASE_DIR / "ssd_templates")).resolve()
    LOG_ROOT = Path(os.getenv("PACKBRIDGE_LOG_ROOT", BASE_DIR / "instance" / "logs")).resolve()
    BACKUP_ROOT = Path(os.getenv("PACKBRIDGE_BACKUP_ROOT", BASE_DIR / "instance" / "backups")).resolve()

    OLLAMA_URL = os.getenv("PACKBRIDGE_OLLAMA_URL", "http://192.168.1.249:11434").rstrip("/")
    OLLAMA_MODEL = os.getenv("PACKBRIDGE_OLLAMA_MODEL", "qwen3:14b")

    OCR_MODE = os.getenv("PACKBRIDGE_OCR_MODE", "off").strip().casefold()
    OCR_LANGUAGE = os.getenv("PACKBRIDGE_OCR_LANGUAGE", "eng").strip() or "eng"

    AUTH_ENABLED = os.getenv("PACKBRIDGE_AUTH_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}
    USERS_FILE = Path(
        os.getenv(
            "PACKBRIDGE_USERS_FILE",
            Path.home() / ".config" / "packbridge" / "users.json",
        )
    ).expanduser().resolve()
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("PACKBRIDGE_COOKIE_SECURE", "0").strip().lower() in {"1", "true", "yes", "on"}

    LOG_LEVEL = os.getenv("PACKBRIDGE_LOG_LEVEL", "INFO")
    LOG_MAX_BYTES = int(os.getenv("PACKBRIDGE_LOG_MAX_BYTES", "5000000"))
    LOG_BACKUP_COUNT = int(os.getenv("PACKBRIDGE_LOG_BACKUP_COUNT", "5"))
    RETENTION_DAYS = int(os.getenv("PACKBRIDGE_RETENTION_DAYS", "90"))
    BACKUP_RETENTION_DAYS = int(os.getenv("PACKBRIDGE_BACKUP_RETENTION_DAYS", "30"))

    SAP_OUTPUT_APPROVED = os.getenv("PACKBRIDGE_SAP_OUTPUT_APPROVED", "0").strip().lower() in {"1", "true", "yes", "on"}
    SAP_SOCS_ONLY_APPROVED = os.getenv("PACKBRIDGE_SAP_SOCS_ONLY_APPROVED", "0").strip().lower() in {"1", "true", "yes", "on"}
    SAP_MACRO_FREE_APPROVED = os.getenv("PACKBRIDGE_SAP_MACRO_FREE_APPROVED", "0").strip().lower() in {"1", "true", "yes", "on"}

    MAX_CONTENT_LENGTH = int(os.getenv("PACKBRIDGE_MAX_UPLOAD_MB", "100")) * 1024 * 1024
    AUTO_CREATE_DB = os.getenv("PACKBRIDGE_AUTO_CREATE_DB", "1").strip().lower() in {"1", "true", "yes", "on"}
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "PACKBRIDGE_DATABASE_URL",
        f"sqlite:///{(BASE_DIR / 'instance' / 'packbridge.sqlite3').resolve()}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
