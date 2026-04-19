from dataclasses import dataclass

import psycopg

from app.models.user import UserModel, UserPreferencesModel
from app.repositories.users import UserRepository


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
