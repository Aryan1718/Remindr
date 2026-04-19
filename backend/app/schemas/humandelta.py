from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class HumanDeltaIndexCreateRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    name: str | None = Field(default=None, max_length=255)
    max_pages: int | None = Field(default=None, ge=1, le=500)

    @field_validator("url", "name")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class HumanDeltaSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=5, ge=1, le=20)
    sources: list[Literal["web", "documents"]] | None = None
    index_id: str | None = Field(default=None, max_length=128)

    @field_validator("query", "index_id")
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class HumanDeltaFsRequest(BaseModel):
    payload_json: dict[str, Any] = Field(default_factory=dict)


class HumanDeltaEnvelope(BaseModel):
    success: bool = True
    data: dict[str, Any]
    message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
