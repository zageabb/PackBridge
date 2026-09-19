from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask


def configure_logging(app: Flask) -> None:
    level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    log_root = Path(app.config["LOG_ROOT"]).expanduser().resolve()
    log_root.mkdir(parents=True, exist_ok=True)
    log_path = log_root / "packbridge.log"

    existing = [
        handler
        for handler in app.logger.handlers
        if isinstance(handler, RotatingFileHandler)
        and getattr(handler, "baseFilename", None) == str(log_path)
    ]
    if not existing:
        handler = RotatingFileHandler(
            log_path,
            maxBytes=int(app.config.get("LOG_MAX_BYTES", 5_000_000)),
            backupCount=int(app.config.get("LOG_BACKUP_COUNT", 5)),
            encoding="utf-8",
        )
        handler.setLevel(level)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s"
            )
        )
        app.logger.addHandler(handler)

    app.logger.setLevel(level)
    app.logger.info(
        "PackBridge logging initialised port=%s auth=%s",
        app.config.get("PACKBRIDGE_PORT"),
        bool(app.config.get("AUTH_ENABLED")),
    )
