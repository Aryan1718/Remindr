from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class NotificationChannel(StrEnum):
    TELEGRAM = "telegram"
    WEB = "web"
    EMAIL = "email"


class NotificationStatus(StrEnum):
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"
    DISMISSED = "dismissed"


@dataclass(slots=True)
class NotificationModel:
    id: str
    user_id: str
    task_id: str | None
    calendar_block_id: str | None
    channel: NotificationChannel
    title: str | None
    body: str
    scheduled_for: datetime | None
    sent_at: datetime | None
    status: NotificationStatus
    provider_message_id: str | None
    metadata_json: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "NotificationModel":
        return cls(
            id=str(record["id"]),
            user_id=str(record["user_id"]),
            task_id=str(record["task_id"]) if record.get("task_id") is not None else None,
            calendar_block_id=str(record["calendar_block_id"]) if record.get("calendar_block_id") is not None else None,
            channel=NotificationChannel(record["channel"]),
            title=record.get("title"),
            body=record["body"],
            scheduled_for=record.get("scheduled_for"),
            sent_at=record.get("sent_at"),
            status=NotificationStatus(record["status"]),
            provider_message_id=record.get("provider_message_id"),
            metadata_json=record.get("metadata_json") or {},
            created_at=record.get("created_at"),
        )
