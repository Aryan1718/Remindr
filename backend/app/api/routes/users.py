from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import get_current_user_snapshot
from app.models.user import UserModel, UserPreferencesModel
from app.schemas.common import SuccessResponse
from app.schemas.user import PreferencesResponse, UserResponse, UserSnapshotResponse

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
