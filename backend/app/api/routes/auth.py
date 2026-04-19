from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends

from app.core.db import get_db_connection
from app.core.security import get_current_token_payload, resolve_user_snapshot
from app.schemas.auth import SessionSyncRequest
from app.schemas.common import SuccessResponse
from app.schemas.user import PreferencesResponse, UserResponse, UserSnapshotResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/session/sync", response_model=SuccessResponse[UserSnapshotResponse])
def sync_session(
    request: SessionSyncRequest,
    payload: dict = Depends(get_current_token_payload),
    connection: psycopg.Connection = Depends(get_db_connection),
) -> SuccessResponse[UserSnapshotResponse]:
    user, preferences = resolve_user_snapshot(
        payload=payload,
        connection=connection,
        full_name_override=request.full_name,
        timezone_override=request.timezone,
    )
    return SuccessResponse(
        data=UserSnapshotResponse(
            user=UserResponse.from_model(user),
            preferences=PreferencesResponse.from_model(preferences),
        )
    )
