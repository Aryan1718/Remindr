from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class ConnectorStatus(StrEnum):
    CONNECTED = "connected"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"


@dataclass(slots=True)
class TelegramConnectorModel:
    id: str
    user_id: str
    provider: str
    status: ConnectorStatus
    account_email: str | None
    access_token_encrypted: str | None
    metadata_json: dict[str, Any] = field(default_factory=dict)
    last_sync_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "TelegramConnectorModel":
        return cls(
            id=str(record["id"]),
            user_id=str(record["user_id"]),
            provider=record["provider"],
            status=ConnectorStatus(record["status"]),
            account_email=record.get("account_email"),
            access_token_encrypted=record.get("access_token_encrypted"),
            metadata_json=record.get("metadata_json") or {},
            last_sync_at=record.get("last_sync_at"),
            created_at=record.get("created_at"),
            updated_at=record.get("updated_at"),
        )
