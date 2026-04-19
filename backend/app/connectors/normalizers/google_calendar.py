from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


def _parse_google_datetime(payload: dict[str, Any], field_name: str) -> tuple[datetime, bool]:
    field_value = payload.get(field_name) or {}
    if not isinstance(field_value, dict):
        raise ValueError(f"google event {field_name} is malformed")

    if field_value.get("dateTime"):
        raw = str(field_value["dateTime"]).replace("Z", "+00:00")
        value = datetime.fromisoformat(raw)
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value, False

    if field_value.get("date"):
        value = datetime.fromisoformat(f"{field_value['date']}T00:00:00+00:00")
        return value, True

    raise ValueError(f"google event {field_name} is missing")


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass(slots=True)
class NormalizedGoogleCalendarEvent:
    user_id: str
    connector_id: str
    external_event_id: str
    calendar_id: str | None
    title: str
    description: str | None
    location: str | None
    starts_at: datetime
    ends_at: datetime
    is_all_day: bool
    status: str | None
    raw_payload_json: dict[str, Any]
    last_synced_at: datetime

    def to_record(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "connector_id": self.connector_id,
            "external_event_id": self.external_event_id,
            "calendar_id": self.calendar_id,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "starts_at": self.starts_at,
            "ends_at": self.ends_at,
            "is_all_day": self.is_all_day,
            "status": self.status,
            "raw_payload_json": self.raw_payload_json,
            "last_synced_at": self.last_synced_at,
        }


def normalize_google_calendar_event(
    *,
    user_id: str,
    connector_id: str,
    raw_event: dict[str, Any],
    last_synced_at: datetime,
) -> NormalizedGoogleCalendarEvent:
    external_event_id = _clean_text(raw_event.get("id"))
    if external_event_id is None:
        raise ValueError("google event id is missing")

    starts_at, start_all_day = _parse_google_datetime(raw_event, "start")
    ends_at, end_all_day = _parse_google_datetime(raw_event, "end")
    is_all_day = start_all_day or end_all_day
    if ends_at <= starts_at:
        raise ValueError("google event end must be after start")

    return NormalizedGoogleCalendarEvent(
        user_id=user_id,
        connector_id=connector_id,
        external_event_id=external_event_id,
        calendar_id=_clean_text(raw_event.get("_calendar_id")),
        title=_clean_text(raw_event.get("summary")) or "Untitled event",
        description=_clean_text(raw_event.get("description")),
        location=_clean_text(raw_event.get("location")),
        starts_at=starts_at,
        ends_at=ends_at,
        is_all_day=is_all_day,
        status=_clean_text(raw_event.get("status")),
        raw_payload_json=dict(raw_event),
        last_synced_at=last_synced_at,
    )
