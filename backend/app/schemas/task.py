from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.task import TaskModel, TaskStatus


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    priority: int = Field(default=3, ge=1, le=5)
    estimated_minutes: int | None = Field(default=None, ge=0)
    energy_required: int | None = Field(default=None, ge=1, le=5)
    due_at: datetime | None = None
    source: str = Field(default="user", max_length=100)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Title cannot be empty")
        return stripped

    @field_validator("description", "source")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    estimated_minutes: int | None = Field(default=None, ge=0)
    actual_minutes: int | None = Field(default=None, ge=0)
    energy_required: int | None = Field(default=None, ge=1, le=5)
    due_at: datetime | None = None
    status: TaskStatus | None = None
    source: str | None = Field(default=None, max_length=100)
    metadata_json: dict[str, Any] | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        return _strip_or_none(value)

    @field_validator("description", "source")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        return _strip_or_none(value)

    @model_validator(mode="after")
    def ensure_update_payload(self) -> "TaskUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class CompleteTaskRequest(BaseModel):
    actual_minutes: int | None = Field(default=None, ge=0)
    completed_at: datetime | None = None


class TaskFilters(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: TaskStatus | None = None
    due_before: datetime | None = None
    due_after: datetime | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    limit: int = Field(default=50, ge=1, le=100)


class TaskRead(BaseModel):
    id: str
    title: str
    description: str | None
    priority: int
    estimated_minutes: int | None
    actual_minutes: int | None
    energy_required: int | None
    due_at: datetime | None
    status: TaskStatus
    source: str
    metadata_json: dict[str, Any]
    created_at: datetime | None
    updated_at: datetime | None
    completed_at: datetime | None

    @classmethod
    def from_model(cls, task: TaskModel) -> "TaskRead":
        return cls(
            id=task.id,
            title=task.title,
            description=task.description,
            priority=task.priority,
            estimated_minutes=task.estimated_minutes,
            actual_minutes=task.actual_minutes,
            energy_required=task.energy_required,
            due_at=task.due_at,
            status=task.status,
            source=task.source,
            metadata_json=task.metadata_json,
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at,
        )


class TaskEnvelope(BaseModel):
    success: bool = True
    data: dict[str, Any]
    message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class TaskListEnvelope(BaseModel):
    success: bool = True
    data: dict[str, Any]
    message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
