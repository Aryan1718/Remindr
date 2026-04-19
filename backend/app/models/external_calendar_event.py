from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ExternalCalendarEventModel:
    id: str
    user_id: str
    connector_id: str
    external_event_id: str
    calendar_id: str | None
    title: str | None
    description: str | None
    location: str | None
    starts_at: datetime
    ends_at: datetime
    is_all_day: bool
    status: str | None
    raw_payload_json: dict[str, Any] = field(default_factory=dict)
    last_synced_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "ExternalCalendarEventModel":
        return cls(
            id=str(record["id"]),
            user_id=str(record["user_id"]),
            connector_id=str(record["connector_id"]),
            external_event_id=record["external_event_id"],
            calendar_id=record.get("calendar_id"),
            title=record.get("title"),
            description=record.get("description"),
            location=record.get("location"),
            starts_at=record["starts_at"],
            ends_at=record["ends_at"],
            is_all_day=bool(record["is_all_day"]),
            status=record.get("status"),
            raw_payload_json=record.get("raw_payload_json") or {},
            last_synced_at=record.get("last_synced_at"),
            created_at=record.get("created_at"),
            updated_at=record.get("updated_at"),
        )
