from __future__ import annotations

import json
from typing import Any

import httpx

from app.llm.base import BaseLLMClient
from app.llm.schemas import ChatMessage, LLMStructuredResult, LLMTextResult, StructuredOutputSchema


class OpenAICompatibleLLM(BaseLLMClient):
    """Thin OpenAI-compatible adapter used by the rest of the backend."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float = 20.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._http_client = http_client or httpx.Client(timeout=timeout_seconds)

    def generate_text(
        self,
        *,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": [message.model_dump() for message in messages],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        data = self._post_chat_completions(payload)
        message = (data.get("choices") or [{}])[0].get("message") or {}
        text = self._coerce_content_to_text(message.get("content"))
        finish_reason = (data.get("choices") or [{}])[0].get("finish_reason")
        return LLMTextResult(text=text, finish_reason=finish_reason, raw_response=data)

    def generate_structured(
        self,
        *,
        messages: list[ChatMessage],
        schema: StructuredOutputSchema,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMStructuredResult:
        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": [message.model_dump() for message in messages],
            "temperature": temperature,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.name,
                    "schema": schema.json_schema,
                },
            },
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        data = self._post_chat_completions(payload)
        message = (data.get("choices") or [{}])[0].get("message") or {}
        text = self._coerce_content_to_text(message.get("content"))
        finish_reason = (data.get("choices") or [{}])[0].get("finish_reason")
        parsed = json.loads(text)
        return LLMStructuredResult(
            parsed=parsed,
            text=text,
            finish_reason=finish_reason,
            raw_response=data,
        )

    def generate_embeddings(
        self,
        *,
        texts: list[str],
        model: str | None = None,
    ) -> list[list[float]]:
        payload: dict[str, Any] = {
            "model": model or self.model,
            "input": texts,
        }
        response = self._http_client.post(
            f"{self.base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        rows = data.get("data") or []
        return [list(row.get("embedding") or []) for row in rows]

    def _post_chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._http_client.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def _coerce_content_to_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_value = item.get("text")
                    if isinstance(text_value, str):
                        text_parts.append(text_value)
            return "\n".join(part.strip() for part in text_parts if part).strip()
        return ""
