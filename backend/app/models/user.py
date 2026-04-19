from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class UserModel:
    id: str
    auth_user_id: str
    email: str | None
    full_name: str | None
    timezone: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "UserModel":
        return cls(
            id=str(record["id"]),
            auth_user_id=str(record["auth_user_id"]),
            email=record.get("email"),
            full_name=record.get("full_name"),
            timezone=record.get("timezone") or "America/Los_Angeles",
            created_at=record.get("created_at"),
            updated_at=record.get("updated_at"),
        )


@dataclass(slots=True)
class UserPreferencesModel:
    id: str
    user_id: str
    sleep_time: str | None = None
    wake_time: str | None = None
    work_start_time: str | None = None
    work_end_time: str | None = None
    work_days: list[int] = field(default_factory=list)
    preferred_response_style: str | None = None
    decision_style_default: str | None = None
    reminder_tolerance: str | None = None
    fatigue_prompt_enabled: bool = True
    onboarding_completed: bool = False
    profile_json: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "UserPreferencesModel":
        return cls(
            id=str(record["id"]),
            user_id=str(record["user_id"]),
            sleep_time=record.get("sleep_time"),
            wake_time=record.get("wake_time"),
            work_start_time=record.get("work_start_time"),
            work_end_time=record.get("work_end_time"),
            work_days=list(record.get("work_days") or [1, 2, 3, 4, 5]),
            preferred_response_style=record.get("preferred_response_style"),
            decision_style_default=record.get("decision_style_default"),
            reminder_tolerance=record.get("reminder_tolerance"),
            fatigue_prompt_enabled=bool(record.get("fatigue_prompt_enabled", True)),
            onboarding_completed=bool(record.get("onboarding_completed", False)),
            profile_json=record.get("profile_json") or {},
            created_at=record.get("created_at"),
            updated_at=record.get("updated_at"),
        )
