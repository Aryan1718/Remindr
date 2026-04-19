from dataclasses import dataclass
from typing import Any

import psycopg

from app.models.user import UserModel, UserPreferencesModel
from app.repositories.users import UserRepository
from app.schemas.user import UserOnboardingUpdateRequest


@dataclass
class UserIdentity:
    auth_user_id: str
    email: str | None = None
    full_name: str | None = None
    timezone: str | None = None


class UserService:
    def __init__(self, connection: psycopg.Connection) -> None:
        self.repository = UserRepository(connection)

    def get_or_create_user_snapshot(
        self,
        identity: UserIdentity,
        *,
        full_name_override: str | None = None,
        timezone_override: str | None = None,
    ) -> tuple[UserModel, UserPreferencesModel]:
        user = self.repository.get_by_auth_user_id(identity.auth_user_id)
        resolved_full_name = full_name_override or identity.full_name
        resolved_timezone = timezone_override or identity.timezone

        if user is None:
            user = self.repository.create_user(
                auth_user_id=identity.auth_user_id,
                email=identity.email,
                full_name=resolved_full_name,
                timezone=resolved_timezone,
            )
        else:
            user = self.repository.update_user(
                user.id,
                email=identity.email,
                full_name=resolved_full_name,
                timezone=resolved_timezone,
            )

        preferences = self.repository.get_preferences(user.id)
        if preferences is None:
            # First authenticated access should establish an internal profile/preferences row.
            preferences = self.repository.create_preferences(user.id)

        return user, preferences

    def update_onboarding_snapshot(
        self,
        *,
        user_id: str,
        payload: UserOnboardingUpdateRequest,
    ) -> tuple[UserModel, UserPreferencesModel]:
        updates = payload.model_dump(exclude_unset=True)
        user_updates: dict[str, Any] = {}
        preference_updates: dict[str, Any] = {}

        if "full_name" in updates:
            user_updates["full_name"] = updates["full_name"]
        if "timezone" in updates:
            user_updates["timezone"] = updates["timezone"]

        preference_fields = {
            "wake_time",
            "sleep_time",
            "work_start_time",
            "work_end_time",
            "preferred_response_style",
            "decision_style_default",
            "reminder_tolerance",
            "fatigue_prompt_enabled",
            "onboarding_completed",
            "profile_json",
        }
        for field in preference_fields:
            if field in updates:
                preference_updates[field] = updates[field]

        user = self.repository.update_user(
            user_id,
            email=None,
            full_name=user_updates.get("full_name"),
            timezone=user_updates.get("timezone"),
        )

        preferences = self.repository.get_preferences(user.id)
        if preferences is None:
            preferences = self.repository.create_preferences(user.id)

        if preference_updates:
            preferences = self.repository.update_preferences(user.id, values=preference_updates)

        return user, preferences
