from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class TaskStatus(StrEnum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    SKIPPED = "skipped"
    ARCHIVED = "archived"


@dataclass(slots=True)
class TaskModel:
    id: str
    user_id: str
    title: str
    description: str | None
    priority: int
    estimated_minutes: int | None
    actual_minutes: int | None
    energy_required: int | None
    due_at: datetime | None
    status: TaskStatus
    source: str
    metadata_json: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "TaskModel":
        return cls(
            id=str(record["id"]),
            user_id=str(record["user_id"]),
            title=record["title"],
            description=record.get("description"),
            priority=record["priority"],
            estimated_minutes=record.get("estimated_minutes"),
            actual_minutes=record.get("actual_minutes"),
            energy_required=record.get("energy_required"),
            due_at=record.get("due_at"),
            status=TaskStatus(record["status"]),
            source=record.get("source") or "user",
            metadata_json=record.get("metadata_json") or {},
            created_at=record.get("created_at"),
            updated_at=record.get("updated_at"),
            completed_at=record.get("completed_at"),
        )
