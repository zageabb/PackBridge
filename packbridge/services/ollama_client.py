from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests
from pydantic import BaseModel, ValidationError


@dataclass(frozen=True)
class OllamaResult:
    available: bool
    value: Any = None
    error_code: str | None = None
    warning: str | None = None
    attempts: int = 0
    model: str | None = None
    endpoint: str | None = None


class OllamaClient:
    """Bounded local Ollama boundary adapted from Should-Cost Intelligence."""

    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        connect_timeout: int = 10,
        read_timeout: int = 300,
        retries: int = 1,
        max_response_bytes: int = 4_000_000,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.retries = retries
        self.max_response_bytes = max_response_bytes
        self.session = session or requests.Session()

    def list_models(self) -> OllamaResult:
        result = self._request("/api/tags", method="GET")
        if not result.available:
            return result
        models = [
            item.get("name") or item.get("model")
            for item in result.value.get("models", [])
            if isinstance(item, dict)
        ]
        return OllamaResult(
            available=True,
            value=[name for name in models if name],
            attempts=result.attempts,
            model=self.model,
            endpoint="/api/tags",
        )

    def generate_text(self, prompt: str) -> OllamaResult:
        result = self._request(
            "/api/generate",
            json_body={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0},
            },
        )
        if not result.available:
            return result
        value = result.value.get("response")
        if not isinstance(value, str) or not value.strip():
            return self._invalid(result, "Ollama response contains no generated text.")
        return OllamaResult(
            available=True,
            value=value.strip(),
            attempts=result.attempts,
            model=self.model,
            endpoint="/api/generate",
        )

    def generate_json(
        self,
        prompt: str,
        response_model: type[BaseModel] | None = None,
    ) -> OllamaResult:
        response_format: str | dict = "json"
        if response_model is not None:
            response_format = response_model.model_json_schema()

        result = self._request(
            "/api/generate",
            json_body={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": response_format,
                "options": {"temperature": 0},
            },
        )
        if not result.available:
            return result
        return self._parse_json(result, result.value.get("response"), response_model)

    def chat(self, messages: list[dict[str, str]], system_prompt: str = "") -> OllamaResult:
        bounded = []
        if system_prompt:
            bounded.append({"role": "system", "content": system_prompt[:30_000]})
        for message in messages[-24:]:
            role = str(message.get("role") or "user")
            msg_content = str(message.get("content") or "")[:30_000]
            bounded.append({"role": role, "content": msg_content})

        result = self._request(
            "/api/chat",
            json_body={
                "model": self.model,
                "messages": bounded,
                "stream": False,
                "options": {"temperature": 0},
            },
        )
        if not result.available:
            return result
        message = result.value.get("message")
        msg_content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(msg_content, str) or not msg_content.strip():
            return self._invalid(result, "Ollama chat response contains no text.")
        return OllamaResult(
            available=True,
            value=msg_content.strip(),
            attempts=result.attempts,
            model=self.model,
            endpoint="/api/chat",
        )

    def _request(
        self,
        endpoint: str,
        *,
        method: str = "POST",
        json_body: dict[str, Any] | None = None,
    ) -> OllamaResult:
        attempts = self.retries + 1
        for attempt in range(1, attempts + 1):
            try:
                response = self.session.request(
                    method,
                    self.base_url + endpoint,
                    json=json_body,
                    timeout=(self.connect_timeout, self.read_timeout),
                )
                response.raise_for_status()
                declared = int(response.headers.get("content-length", 0) or 0)
                if declared > self.max_response_bytes or len(response.content) > self.max_response_bytes:
                    return OllamaResult(
                        available=False,
                        error_code="RESPONSE_TOO_LARGE",
                        warning="Ollama response exceeded the configured size limit.",
                        attempts=attempt,
                        model=self.model,
                        endpoint=endpoint,
                    )
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("response root is not an object")
                return OllamaResult(
                    available=True,
                    value=payload,
                    attempts=attempt,
                    model=self.model,
                    endpoint=endpoint,
                )
            except requests.Timeout:
                if attempt == attempts:
                    return OllamaResult(False, error_code="TIMEOUT", warning="Ollama request timed out.", attempts=attempt, model=self.model, endpoint=endpoint)
            except requests.ConnectionError:
                if attempt == attempts:
                    return OllamaResult(False, error_code="CONNECTION_ERROR", warning="Ollama service is unavailable.", attempts=attempt, model=self.model, endpoint=endpoint)
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else "unknown"
                return OllamaResult(False, error_code="HTTP_ERROR", warning=f"Ollama request failed with HTTP {status}.", attempts=attempt, model=self.model, endpoint=endpoint)
            except (ValueError, json.JSONDecodeError, TypeError):
                return OllamaResult(False, error_code="INVALID_RESPONSE", warning="Ollama returned an invalid response.", attempts=attempt, model=self.model, endpoint=endpoint)
        raise AssertionError("unreachable")

    def _parse_json(
        self,
        result: OllamaResult,
        content: Any,
        response_model: type[BaseModel] | None,
    ) -> OllamaResult:
        if not isinstance(content, str) or not content.strip():
            return self._invalid(result, "Ollama response contains no JSON content.")
        text = content.strip()
        if text.startswith("~~~") and text.endswith("~~~"):
            lines = text.splitlines()
            if len(lines) >= 3:
                text = "\n".join(lines[1:-1]).strip()
        try:
            parsed = json.loads(text)
            value = response_model.model_validate(parsed) if response_model else parsed
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
            return self._invalid(result, "Ollama returned JSON that does not match the required schema.")
        return OllamaResult(True, value=value, attempts=result.attempts, model=self.model, endpoint=result.endpoint)

    @staticmethod
    def _invalid(result: OllamaResult, warning: str) -> OllamaResult:
        return OllamaResult(False, error_code="INVALID_RESPONSE", warning=warning, attempts=result.attempts, model=result.model, endpoint=result.endpoint)
