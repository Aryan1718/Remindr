from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.internal_calendar import (
    CalendarBlockStatus,
    CalendarBlockType,
    CalendarFeedbackModel,
    FeedbackResponseType,
    InternalCalendarBlockModel,
)
from app.schemas.task import TaskRead


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class InternalCalendarSuggestRequest(BaseModel):
    task_ids: list[str] | None = None
    window_start: datetime
    window_end: datetime
    max_suggestions: int = Field(default=5, ge=1, le=25)
    sync_to_google_default: bool = False

    @model_validator(mode="after")
    def validate_window(self) -> "InternalCalendarSuggestRequest":
        if self.window_start >= self.window_end:
            raise ValueError("window_start must be before window_end")
        return self


class InternalCalendarListFilters(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    start: datetime | None = None
    end: datetime | None = None
    status: CalendarBlockStatus | None = None
    task_id: str | None = None
    limit: int = Field(default=100, ge=1, le=200)

    @model_validator(mode="after")
    def validate_range(self) -> "InternalCalendarListFilters":
        if self.start is not None and self.end is not None and self.start > self.end:
            raise ValueError("start must be before end")
        return self


class InternalCalendarConfirmRequest(BaseModel):
    sync_to_google: bool | None = None
    fatigue_score: int | None = Field(default=None, ge=0, le=5)
    reason_text: str | None = None

    @field_validator("reason_text")
    @classmethod
    def normalize_reason_text(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class InternalCalendarRejectRequest(BaseModel):
    reason_code: str | None = Field(default=None, max_length=100)
    reason_text: str | None = None
    fatigue_score: int | None = Field(default=None, ge=0, le=5)

    @field_validator("reason_code", "reason_text")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        return _strip_or_none(value)

    @model_validator(mode="after")
    def validate_reason(self) -> "InternalCalendarRejectRequest":
        if self.reason_code is None and self.reason_text is None:
            raise ValueError("reason_code or reason_text is required")
        return self


class InternalCalendarRescheduleRequest(BaseModel):
    new_starts_at: datetime | None = None
    new_ends_at: datetime | None = None
    auto_find_new_slot: bool = False
    reason_code: str | None = Field(default=None, max_length=100)
    reason_text: str | None = None
    fatigue_score: int | None = Field(default=None, ge=0, le=5)

    @field_validator("reason_code", "reason_text")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        return _strip_or_none(value)

    @model_validator(mode="after")
    def validate_request(self) -> "InternalCalendarRescheduleRequest":
        has_explicit = self.new_starts_at is not None or self.new_ends_at is not None
        if self.auto_find_new_slot and has_explicit:
            raise ValueError("Provide either explicit times or auto_find_new_slot")
        if not self.auto_find_new_slot:
            if self.new_starts_at is None or self.new_ends_at is None:
                raise ValueError("new_starts_at and new_ends_at are required for explicit reschedule")
            if self.new_starts_at >= self.new_ends_at:
                raise ValueError("new_starts_at must be before new_ends_at")
        return self


class InternalCalendarCompleteRequest(BaseModel):
    task_completed: bool = False
    notes: str | None = None

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class InternalCalendarFeedbackCreateRequest(BaseModel):
    response_type: FeedbackResponseType
    reason_code: str | None = Field(default=None, max_length=100)
    reason_text: str | None = None
    fatigue_score: int | None = Field(default=None, ge=0, le=5)

    @field_validator("reason_code", "reason_text")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class CalendarFeedbackRead(BaseModel):
    id: str
    calendar_block_id: str
    response_type: FeedbackResponseType
    reason_code: str | None
    reason_text: str | None
    fatigue_score: int | None
    created_at: datetime | None

    @classmethod
    def from_model(cls, feedback: CalendarFeedbackModel) -> "CalendarFeedbackRead":
        return cls(
            id=feedback.id,
            calendar_block_id=feedback.calendar_block_id,
            response_type=feedback.response_type,
            reason_code=feedback.reason_code,
            reason_text=feedback.reason_text,
            fatigue_score=feedback.fatigue_score,
            created_at=feedback.created_at,
        )


class InternalCalendarBlockRead(BaseModel):
    id: str
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
    metadata_json: dict[str, Any]
    created_at: datetime | None
    updated_at: datetime | None
    confirmed_at: datetime | None
    rejected_at: datetime | None
    completed_at: datetime | None

    @classmethod
    def from_model(cls, block: InternalCalendarBlockModel) -> "InternalCalendarBlockRead":
        return cls(
            id=block.id,
            task_id=block.task_id,
            title=block.title,
            block_type=block.block_type,
            starts_at=block.starts_at,
            ends_at=block.ends_at,
            status=block.status,
            sync_to_google=block.sync_to_google,
            external_event_id=block.external_event_id,
            source=block.source,
            reason_summary=block.reason_summary,
            reschedule_count=block.reschedule_count,
            priority_snapshot=block.priority_snapshot,
            energy_snapshot=block.energy_snapshot,
            metadata_json=block.metadata_json,
            created_at=block.created_at,
            updated_at=block.updated_at,
            confirmed_at=block.confirmed_at,
            rejected_at=block.rejected_at,
            completed_at=block.completed_at,
        )


class InternalCalendarSuggestEnvelope(BaseModel):
    success: bool = True
    data: dict[str, Any]
    message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class InternalCalendarListEnvelope(BaseModel):
    success: bool = True
    data: dict[str, Any]
    message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class InternalCalendarDetailEnvelope(BaseModel):
    success: bool = True
    data: dict[str, Any]
    message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class InternalCalendarMutationEnvelope(BaseModel):
    success: bool = True
    data: dict[str, Any]
    message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class CalendarFeedbackEnvelope(BaseModel):
    success: bool = True
    data: dict[str, Any]
    message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class InternalCalendarCompletionResult(BaseModel):
    block: InternalCalendarBlockRead
    task: TaskRead | None = None
