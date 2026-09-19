from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from flask import current_app, session
from werkzeug.security import check_password_hash, generate_password_hash


ROLE_CAPABILITIES = {
    "viewer": {"read"},
    "processor": {"read", "process", "edit", "chat", "project"},
    "approver": {
        "read", "process", "edit", "chat", "project",
        "validation_approve", "output_generate",
    },
    "knowledge_admin": {
        "read", "process", "edit", "chat", "project",
        "knowledge_manage",
    },
    "admin": {
        "read", "process", "edit", "chat", "project",
        "validation_approve", "output_generate", "knowledge_manage",
        "settings_manage", "admin",
    },
}


@dataclass(frozen=True)
class Identity:
    username: str
    role: str

    def can(self, capability: str) -> bool:
        return capability in ROLE_CAPABILITIES.get(self.role, set())


class AuthConfigurationError(ValueError):
    pass


def users_file() -> Path:
    return Path(current_app.config["USERS_FILE"]).expanduser().resolve()


def load_users() -> dict[str, dict]:
    path = users_file()
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthConfigurationError(f"Could not read PackBridge users file: {exc}") from exc

    users = payload.get("users") if isinstance(payload, dict) else None
    if not isinstance(users, list):
        raise AuthConfigurationError("Users file must contain a top-level 'users' list.")

    result = {}
    for item in users:
        if not isinstance(item, dict):
            continue
        username = str(item.get("username") or "").strip()
        role = str(item.get("role") or "").strip()
        password_hash = str(item.get("password_hash") or "").strip()
        if not username or role not in ROLE_CAPABILITIES or not password_hash:
            continue
        result[username] = {
            "username": username,
            "role": role,
            "password_hash": password_hash,
        }
    return result


def authenticate(username: str, password: str) -> Identity | None:
    record = load_users().get(str(username or "").strip())
    if not record:
        return None
    if not check_password_hash(record["password_hash"], str(password or "")):
        return None
    return Identity(record["username"], record["role"])


def current_identity() -> Identity | None:
    if not current_app.config.get("AUTH_ENABLED", False):
        return Identity("local-user", "admin")
    value = session.get("packbridge_user")
    if not isinstance(value, dict):
        return None
    username = str(value.get("username") or "").strip()
    role = str(value.get("role") or "").strip()
    if not username or role not in ROLE_CAPABILITIES:
        return None
    return Identity(username, role)


def login_identity(identity: Identity) -> None:
    session["packbridge_user"] = {
        "username": identity.username,
        "role": identity.role,
    }


def logout_identity() -> None:
    session.pop("packbridge_user", None)


def capability_for_endpoint(endpoint: str | None, method: str) -> str:
    endpoint = endpoint or ""
    method = method.upper()

    if endpoint.startswith("settings."):
        return "settings_manage"

    if method in {"GET", "HEAD", "OPTIONS"}:
        return "read"


    if endpoint in {"knowledge.apply", "knowledge.reject"}:
        return "knowledge_manage"
    if endpoint.startswith("knowledge."):
        return "edit"

    if endpoint in {
        "jobs.acknowledge_validation_issue",
        "jobs.reopen_validation_issue",
    }:
        return "validation_approve"

    if endpoint in {
        "projects.build_validation_workbook",
        "projects.build_production_workbook",
    }:
        return "output_generate"

    if endpoint.startswith("projects."):
        return "project"

    if endpoint in {"jobs.chat"}:
        return "chat"

    if endpoint.startswith("jobs."):
        return "process"

    return "read"


def role_options() -> Iterable[str]:
    return ROLE_CAPABILITIES.keys()


def password_hash(password: str) -> str:
    if len(str(password or "")) < 10:
        raise ValueError("Use a password of at least 10 characters.")
    return generate_password_hash(password)
