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

    def _cloud_tagged(self) -> bool:
        return "cloud" in self.model.casefold()

    @staticmethod
    def _schema_instruction(
        prompt: str,
        response_model: type[BaseModel],
    ) -> str:
        schema = json.dumps(
            response_model.model_json_schema(),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return (
            prompt.rstrip()
            + "\n\nIMPORTANT STRUCTURED OUTPUT REQUIREMENT\n"
            + "Return exactly one JSON object matching this JSON Schema. "
            + "Do not add prose, markdown, comments or extra keys.\n"
            + schema
        )

    @staticmethod
    def _extract_json_text(content: str) -> str:
        text = content.strip()
        fenced_tilde = text.startswith("~~~") and text.endswith("~~~")
        fenced_backtick = text.startswith(chr(96) * 3) and text.endswith(chr(96) * 3)
        if fenced_tilde or fenced_backtick:
            lines = text.splitlines()
            if len(lines) >= 3:
                text = "\n".join(lines[1:-1]).strip()

        try:
            json.loads(text)
            return text
        except (json.JSONDecodeError, TypeError):
            pass

        decoder = json.JSONDecoder()
        starts = [
            index
            for index, character in enumerate(text)
            if character in "[{"
        ]
        for index in starts:
            try:
                _, end = decoder.raw_decode(text[index:])
                candidate = text[index:index + end]
                json.loads(candidate)
                return candidate
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
        return text

    def _repair_structured_json(
        self,
        original_prompt: str,
        invalid_content: str,
        response_model: type[BaseModel],
    ) -> OllamaResult:
        schema = json.dumps(
            response_model.model_json_schema(),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        repair_prompt = (
            "Repair the candidate JSON so it matches the required schema exactly. "
            "Do not invent document facts and do not reinterpret values. "
            "Only repair JSON structure, field names, wrappers, missing default objects, "
            "and remove unsupported extra keys. Return JSON only.\n\n"
            "REQUIRED SCHEMA:\n"
            + schema
            + "\n\nCANDIDATE JSON/OUTPUT:\n"
            + str(invalid_content)[:60_000]
            + "\n\nORIGINAL TASK CONTEXT (for field meaning only):\n"
            + original_prompt[:30_000]
        )
        result = self._request(
            "/api/generate",
            json_body={
                "model": self.model,
                "prompt": repair_prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            },
        )
        if not result.available:
            return result
        return self._parse_json(
            result,
            result.value.get("response"),
            response_model,
            allow_repair=False,
            original_prompt=original_prompt,
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
        request_prompt = prompt
        response_format: str | dict = "json"

        if response_model is not None:
            if self._cloud_tagged():
                # Cloud-backed Ollama models are not all equally reliable with
                # native JSON-Schema constrained decoding. JSON mode plus the
                # explicit schema avoids a known provider compatibility failure.
                response_format = "json"
                request_prompt = self._schema_instruction(prompt, response_model)
            else:
                response_format = response_model.model_json_schema()

        result = self._request(
            "/api/generate",
            json_body={
                "model": self.model,
                "prompt": request_prompt,
                "stream": False,
                "format": response_format,
                "options": {"temperature": 0},
            },
        )
        if not result.available:
            # Some provider/model combinations reject a JSON Schema in the
            # format field while still supporting ordinary JSON mode.
            if response_model is not None and not self._cloud_tagged():
                fallback = self._request(
                    "/api/generate",
                    json_body={
                        "model": self.model,
                        "prompt": self._schema_instruction(prompt, response_model),
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0},
                    },
                )
                if fallback.available:
                    return self._parse_json(
                        fallback,
                        fallback.value.get("response"),
                        response_model,
                        original_prompt=prompt,
                    )
            return result

        return self._parse_json(
            result,
            result.value.get("response"),
            response_model,
            original_prompt=prompt,
        )

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

    def chat_json(
        self,
        messages: list[dict[str, str]],
        response_model: type[BaseModel],
        system_prompt: str = "",
    ) -> OllamaResult:
        bounded = []
        response_format: str | dict = response_model.model_json_schema()
        effective_system = system_prompt

        if self._cloud_tagged():
            response_format = "json"
            effective_system = self._schema_instruction(
                system_prompt or "Return the requested structured response.",
                response_model,
            )

        if effective_system:
            bounded.append({"role": "system", "content": effective_system[:45_000]})
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
                "format": response_format,
                "options": {"temperature": 0},
            },
        )
        if not result.available:
            return result
        message = result.value.get("message")
        msg_content = message.get("content") if isinstance(message, dict) else None
        return self._parse_json(
            result,
            msg_content,
            response_model,
            original_prompt=effective_system,
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
        *,
        allow_repair: bool = True,
        original_prompt: str = "",
    ) -> OllamaResult:
        if not isinstance(content, str) or not content.strip():
            return self._invalid(result, "Ollama response contains no JSON content.")

        text = self._extract_json_text(content)
        try:
            parsed = json.loads(text)
            # Some provider-backed Ollama models return a JSON string whose
            # contents are the actual JSON object. Unwrap at most two layers.
            for _ in range(2):
                if not isinstance(parsed, str):
                    break
                candidate = parsed.strip()
                if not candidate or candidate[0] not in "[{":
                    break
                parsed = json.loads(candidate)
        except (json.JSONDecodeError, TypeError, ValueError):
            if allow_repair and response_model is not None:
                return self._repair_structured_json(
                    original_prompt,
                    content,
                    response_model,
                )
            return self._invalid(
                result,
                "Ollama returned content that could not be parsed as JSON.",
            )

        if response_model is None:
            return OllamaResult(
                True,
                value=parsed,
                attempts=result.attempts,
                model=self.model,
                endpoint=result.endpoint,
            )

        try:
            value = response_model.model_validate(parsed)
        except ValidationError as exc:
            if allow_repair:
                return self._repair_structured_json(
                    original_prompt,
                    text,
                    response_model,
                )
            details = exc.errors()[:3]
            summary = "; ".join(
                f"{'.'.join(str(part) for part in item.get('loc', ()))}: {item.get('msg', 'invalid')}"
                for item in details
            )
            return self._invalid(
                result,
                "Ollama returned JSON that does not match the required schema"
                + (f" ({summary})." if summary else "."),
            )
        except (TypeError, ValueError) as exc:
            return self._invalid(
                result,
                f"Ollama returned JSON that could not be validated: {exc}",
            )

        return OllamaResult(
            True,
            value=value,
            attempts=result.attempts,
            model=self.model,
            endpoint=result.endpoint,
        )

    @staticmethod
    def _invalid(result: OllamaResult, warning: str) -> OllamaResult:
        return OllamaResult(False, error_code="INVALID_RESPONSE", warning=warning, attempts=result.attempts, model=result.model, endpoint=result.endpoint)
