from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from flask import current_app

from .ollama_client import OllamaClient


def _settings_path() -> Path:
    return Path(current_app.instance_path) / "app-settings.json"


def normalize_url(value: str) -> str:
    url = value.strip().rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Enter a valid Ollama URL, for example http://192.168.1.249:11434")
    return url


def current() -> dict:
    path = _settings_path()
    values = {}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                values = loaded
        except (OSError, json.JSONDecodeError):
            values = {}
    return {
        "ollama_url": str(values.get("ollama_url") or current_app.config["OLLAMA_URL"]).rstrip("/"),
        "ollama_model": str(values.get("ollama_model") or current_app.config["OLLAMA_MODEL"]),
    }


def save(values: dict) -> dict:
    existing = current()
    updated = {
        "ollama_url": normalize_url(str(values.get("ollama_url") or existing["ollama_url"])),
        "ollama_model": str(values.get("ollama_model") or existing["ollama_model"]).strip(),
    }
    if not updated["ollama_model"]:
        raise ValueError("Ollama model is required.")
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return updated


def client() -> OllamaClient:
    settings = current()
    return OllamaClient(settings["ollama_url"], settings["ollama_model"])


def test_connection(url: str | None = None, model: str | None = None) -> dict:
    settings = current()
    target_url = normalize_url(url) if url else settings["ollama_url"]
    target_model = (model if model is not None else settings["ollama_model"]).strip()
    result = OllamaClient(target_url, target_model, read_timeout=15, retries=0).list_models()
    if not result.available:
        return {
            "connected": False,
            "url": target_url,
            "models": [],
            "selected_model": target_model,
            "model_available": False,
            "error": result.warning or result.error_code,
        }
    models = result.value
    return {
        "connected": True,
        "url": target_url,
        "models": models,
        "selected_model": target_model,
        "model_available": target_model in models,
    }
