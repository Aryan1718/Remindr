from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class NormalizedIntent(BaseModel):
    intent_type: Literal[
        "CREATE_TASK",
        "GET_TASKS",
        "NEXT_ACTION",
        "PLAN_DAY",
        "GENERAL_DECISION",
        "CALENDAR_ACTION",
        "UNKNOWN",
    ]
    raw_text: str
    entities: dict = Field(default_factory=dict)
    context: dict = Field(default_factory=dict)
    task_title: str | None = None
    due_at: datetime | None = None
    time_available_minutes: int | None = None
    fatigue_score: int | None = None
