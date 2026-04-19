from __future__ import annotations

import psycopg

from fastapi import APIRouter, Depends

from app.core.db import get_db_connection
from app.core.security import get_current_user_snapshot
from app.models.user import UserModel, UserPreferencesModel
from app.schemas.common import SuccessResponse
from app.schemas.user import (
    PreferencesResponse,
    UserOnboardingUpdateRequest,
    UserResponse,
    UserSnapshotResponse,
)
from app.services.user_service import UserService

router = APIRouter(tags=["users"])


@router.get("/me", response_model=SuccessResponse[UserSnapshotResponse])
def get_me(
    snapshot: tuple[UserModel, UserPreferencesModel] = Depends(get_current_user_snapshot),
) -> SuccessResponse[UserSnapshotResponse]:
    user, preferences = snapshot
    return SuccessResponse(
        data=UserSnapshotResponse(
            user=UserResponse.from_model(user),
            preferences=PreferencesResponse.from_model(preferences),
        )
    )


@router.patch("/me", response_model=SuccessResponse[UserSnapshotResponse])
def update_me(
    payload: UserOnboardingUpdateRequest,
    snapshot: tuple[UserModel, UserPreferencesModel] = Depends(get_current_user_snapshot),
    connection: psycopg.Connection = Depends(get_db_connection),
) -> SuccessResponse[UserSnapshotResponse]:
    user, _ = snapshot
    updated_user, updated_preferences = UserService(connection).update_onboarding_snapshot(
        user_id=user.id,
        payload=payload,
    )
    return SuccessResponse(
        data=UserSnapshotResponse(
            user=UserResponse.from_model(updated_user),
            preferences=PreferencesResponse.from_model(updated_preferences),
        )
    )
