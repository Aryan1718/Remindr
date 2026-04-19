from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.user import UserModel, UserPreferencesModel


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _time_to_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


class UserResponse(BaseModel):
    id: str
    auth_user_id: str
    email: str | None = None
    full_name: str | None = None
    timezone: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, user: UserModel) -> "UserResponse":
        return cls(
            id=user.id,
            auth_user_id=user.auth_user_id,
            email=user.email,
            full_name=user.full_name,
            timezone=user.timezone,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class PreferencesResponse(BaseModel):
    user_id: str
    sleep_time: str | None = None
    wake_time: str | None = None
    work_start_time: str | None = None
    work_end_time: str | None = None
    work_days: list[int] = Field(default_factory=list)
    preferred_response_style: str | None = None
    decision_style_default: str | None = None
    reminder_tolerance: str | None = None
    fatigue_prompt_enabled: bool
    onboarding_completed: bool
    profile_json: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, preferences: UserPreferencesModel) -> "PreferencesResponse":
        return cls(
            user_id=preferences.user_id,
            sleep_time=_time_to_string(preferences.sleep_time),
            wake_time=_time_to_string(preferences.wake_time),
            work_start_time=_time_to_string(preferences.work_start_time),
            work_end_time=_time_to_string(preferences.work_end_time),
            work_days=preferences.work_days,
            preferred_response_style=preferences.preferred_response_style,
            decision_style_default=preferences.decision_style_default,
            reminder_tolerance=preferences.reminder_tolerance,
            fatigue_prompt_enabled=preferences.fatigue_prompt_enabled,
            onboarding_completed=preferences.onboarding_completed,
            profile_json=preferences.profile_json,
        )


class UserSnapshotResponse(BaseModel):
    user: UserResponse
    preferences: PreferencesResponse


class UserOnboardingUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    timezone: str | None = Field(default=None, max_length=100)
    wake_time: str | None = None
    sleep_time: str | None = None
    work_start_time: str | None = None
    work_end_time: str | None = None
    preferred_response_style: str | None = Field(default=None, max_length=100)
    decision_style_default: str | None = Field(default=None, max_length=100)
    reminder_tolerance: str | None = Field(default=None, max_length=100)
    fatigue_prompt_enabled: bool | None = None
    onboarding_completed: bool | None = None
    profile_json: dict[str, Any] | None = None

    @field_validator(
        "full_name",
        "timezone",
        "wake_time",
        "sleep_time",
        "work_start_time",
        "work_end_time",
        "preferred_response_style",
        "decision_style_default",
        "reminder_tolerance",
    )
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        return _strip_or_none(value)

    @model_validator(mode="after")
    def ensure_payload(self) -> "UserOnboardingUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self
