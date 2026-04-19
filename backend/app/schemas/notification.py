from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.notification import NotificationChannel, NotificationModel, NotificationStatus


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class NotificationListFilters(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: NotificationStatus | None = None
    channel: NotificationChannel | None = None
    scheduled_before: datetime | None = None
    scheduled_after: datetime | None = None
    limit: int = Field(default=50, ge=1, le=100)


class NotificationCreateRequest(BaseModel):
    channel: NotificationChannel = NotificationChannel.TELEGRAM
    title: str | None = Field(default=None, max_length=200)
    body: str = Field(min_length=1, max_length=4000)

    @field_validator("title", "body")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class NotificationDismissRequest(BaseModel):
    pass


class NotificationRead(BaseModel):
    id: str
    task_id: str | None
    calendar_block_id: str | None
    channel: NotificationChannel
    title: str | None
    body: str
    scheduled_for: datetime | None
    sent_at: datetime | None
    status: NotificationStatus
    provider_message_id: str | None
    metadata_json: dict[str, Any]
    created_at: datetime | None

    @classmethod
    def from_model(cls, notification: NotificationModel) -> "NotificationRead":
        return cls(
            id=notification.id,
            task_id=notification.task_id,
            calendar_block_id=notification.calendar_block_id,
            channel=notification.channel,
            title=notification.title,
            body=notification.body,
            scheduled_for=notification.scheduled_for,
            sent_at=notification.sent_at,
            status=notification.status,
            provider_message_id=notification.provider_message_id,
            metadata_json=notification.metadata_json,
            created_at=notification.created_at,
        )


class NotificationEnvelope(BaseModel):
    success: bool = True
    data: dict[str, Any]
    message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class NotificationListEnvelope(BaseModel):
    success: bool = True
    data: dict[str, Any]
    message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
