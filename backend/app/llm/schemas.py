from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ChatRole = Literal["system", "user", "assistant", "tool"]


class ChatMessage(BaseModel):
    role: ChatRole
    content: str


class StructuredOutputSchema(BaseModel):
    name: str = "response"
    json_schema: dict[str, Any]


class LLMTextResult(BaseModel):
    text: str
    finish_reason: str | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)


class LLMStructuredResult(BaseModel):
    parsed: dict[str, Any]
    text: str
    finish_reason: str | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)
