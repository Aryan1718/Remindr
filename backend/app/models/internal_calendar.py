from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class CalendarBlockType(StrEnum):
    SUGGESTED_TASK = "suggested_task"
    FOCUS_BLOCK = "focus_block"
    BREAK_BLOCK = "break_block"
    DEADLINE_BUFFER = "deadline_buffer"
    MANUAL_BLOCK = "manual_block"
    REVIEW_BLOCK = "review_block"
    RECOVERY_BLOCK = "recovery_block"


class CalendarBlockStatus(StrEnum):
    SUGGESTED = "suggested"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    RESCHEDULED = "rescheduled"
    DONE = "done"
    MISSED = "missed"
    CANCELLED = "cancelled"


class FeedbackResponseType(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MOVED = "moved"
    SNOOZED = "snoozed"
    COMPLETED = "completed"
    IGNORED = "ignored"


@dataclass(slots=True)
class InternalCalendarBlockModel:
    id: str
    user_id: str
    task_id: str | None
    title: str
    block_type: CalendarBlockType
    starts_at: datetime
    ends_at: datetime
    status: CalendarBlockStatus
    sync_to_google: bool
    external_event_id: str | None
    source: str
    reason_summary: str | None
    reschedule_count: int
    priority_snapshot: int | None
    energy_snapshot: int | None
    metadata_json: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    confirmed_at: datetime | None = None
    rejected_at: datetime | None = None
    completed_at: datetime | None = None

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "InternalCalendarBlockModel":
        return cls(
            id=str(record["id"]),
            user_id=str(record["user_id"]),
            task_id=str(record["task_id"]) if record.get("task_id") is not None else None,
            title=record["title"],
            block_type=CalendarBlockType(record["block_type"]),
            starts_at=record["starts_at"],
            ends_at=record["ends_at"],
            status=CalendarBlockStatus(record["status"]),
            sync_to_google=record["sync_to_google"],
            external_event_id=record.get("external_event_id"),
            source=record.get("source") or "system",
            reason_summary=record.get("reason_summary"),
            reschedule_count=record["reschedule_count"],
            priority_snapshot=record.get("priority_snapshot"),
            energy_snapshot=record.get("energy_snapshot"),
            metadata_json=record.get("metadata_json") or {},
            created_at=record.get("created_at"),
            updated_at=record.get("updated_at"),
            confirmed_at=record.get("confirmed_at"),
            rejected_at=record.get("rejected_at"),
            completed_at=record.get("completed_at"),
        )


@dataclass(slots=True)
class CalendarFeedbackModel:
    id: str
    calendar_block_id: str
    user_id: str
    response_type: FeedbackResponseType
    reason_code: str | None
    reason_text: str | None
    fatigue_score: int | None
    created_at: datetime | None = None

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "CalendarFeedbackModel":
        return cls(
            id=str(record["id"]),
            calendar_block_id=str(record["calendar_block_id"]),
            user_id=str(record["user_id"]),
            response_type=FeedbackResponseType(record["response_type"]),
            reason_code=record.get("reason_code"),
            reason_text=record.get("reason_text"),
            fatigue_score=record.get("fatigue_score"),
            created_at=record.get("created_at"),
        )
