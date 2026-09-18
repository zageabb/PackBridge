from __future__ import annotations

from pathlib import Path

from flask import current_app


def prompts_root() -> Path:
    return Path(current_app.root_path).parent / "llm_prompts"


def load_prompt(name: str) -> str:
    path = prompts_root() / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Prompt not found: {name}")
    return path.read_text(encoding="utf-8")


def render_prompt(name: str, **values) -> str:
    content = load_prompt(name)
    for key, value in values.items():
        content = content.replace("{{" + key + "}}", str(value))
    return content
