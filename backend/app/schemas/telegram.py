from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.telegram import ConnectorStatus, TelegramConnectorModel


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class TelegramConnectRequest(BaseModel):
    bot_token: str = Field(min_length=10, max_length=256)
    webhook_base_url: str | None = Field(default=None, max_length=512)

    @field_validator("bot_token", "webhook_base_url")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class TelegramWebhookResult(BaseModel):
    linked: bool
    update_type: str
    event_id: str


class TelegramConnectionRead(BaseModel):
    id: str
    user_id: str
    status: ConnectorStatus
    bot_username: str | None
    bot_first_name: str | None
    bot_id: int | None
    bot_token_hint: str
    telegram_user_id: int | None
    telegram_chat_id: int | None
    webhook_url: str | None
    webhook_secret: str | None
    webhook_status: str
    last_event_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_model(cls, connector: TelegramConnectorModel) -> "TelegramConnectionRead":
        metadata = connector.metadata_json or {}
        return cls(
            id=connector.id,
            user_id=connector.user_id,
            status=connector.status,
            bot_username=metadata.get("bot_username"),
            bot_first_name=metadata.get("bot_first_name"),
            bot_id=metadata.get("bot_id"),
            bot_token_hint=metadata.get("bot_token_hint") or "",
            telegram_user_id=metadata.get("telegram_user_id"),
            telegram_chat_id=metadata.get("telegram_chat_id"),
            webhook_url=metadata.get("webhook_url"),
            webhook_secret=metadata.get("webhook_secret"),
            webhook_status=metadata.get("webhook_status") or "not_configured",
            last_event_at=metadata.get("last_event_at"),
            updated_at=connector.updated_at,
        )


class TelegramEventRead(BaseModel):
    id: str
    event_type: str
    entity_type: str | None
    entity_id: str | None
    payload_json: dict[str, Any]
    created_at: datetime | None


class TelegramConnectionEnvelope(BaseModel):
    success: bool = True
    data: dict[str, Any]
    message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class TelegramEventListEnvelope(BaseModel):
    success: bool = True
    data: dict[str, Any]
    message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
