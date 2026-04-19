from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class ConnectorProvider(StrEnum):
    GMAIL = "gmail"
    GOOGLE_CALENDAR = "google_calendar"
    GOOGLE_NOTES = "google_notes"
    TELEGRAM = "telegram"


class ConnectorStatus(StrEnum):
    CONNECTED = "connected"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"


@dataclass(slots=True)
class ConnectorModel:
    id: str
    user_id: str
    provider: ConnectorProvider
    status: ConnectorStatus
    account_email: str | None
    access_token_encrypted: str | None
    refresh_token_encrypted: str | None
    token_expires_at: datetime | None
    metadata_json: dict[str, Any] = field(default_factory=dict)
    last_sync_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "ConnectorModel":
        return cls(
            id=str(record["id"]),
            user_id=str(record["user_id"]),
            provider=ConnectorProvider(record["provider"]),
            status=ConnectorStatus(record["status"]),
            account_email=record.get("account_email"),
            access_token_encrypted=record.get("access_token_encrypted"),
            refresh_token_encrypted=record.get("refresh_token_encrypted"),
            token_expires_at=record.get("token_expires_at"),
            metadata_json=record.get("metadata_json") or {},
            last_sync_at=record.get("last_sync_at"),
            created_at=record.get("created_at"),
            updated_at=record.get("updated_at"),
        )
