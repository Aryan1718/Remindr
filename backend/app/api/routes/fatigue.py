from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, status

from app.core.db import get_db_connection
from app.core.security import AuthenticatedUser, get_current_user
from app.schemas.common import SuccessResponse
from app.schemas.fatigue import (
    FatigueCheckinCreateRequest,
    FatigueCheckinListFilters,
    FatigueCheckinListResponseData,
    FatigueCheckinResponseData,
    FatiguePatternFilters,
    FatiguePatternListResponseData,
    FatiguePatternRecomputeRequest,
    FatiguePatternRecomputeResponseData,
)
from app.services.fatigue_service import FatigueService

router = APIRouter(prefix="/fatigue", tags=["fatigue"])


def get_fatigue_service(connection: psycopg.Connection = Depends(get_db_connection)) -> FatigueService:
    return FatigueService(connection)


@router.post("/checkins", response_model=SuccessResponse[FatigueCheckinResponseData], status_code=status.HTTP_201_CREATED)
def create_fatigue_checkin(
    payload: FatigueCheckinCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: FatigueService = Depends(get_fatigue_service),
) -> SuccessResponse[FatigueCheckinResponseData]:
    checkin = service.create_checkin(user_id=current_user.user_id, payload=payload)
    return SuccessResponse(data=FatigueCheckinResponseData(checkin=checkin), message="Fatigue check-in created")


@router.get("/checkins", response_model=SuccessResponse[FatigueCheckinListResponseData])
def list_fatigue_checkins(
    filters: FatigueCheckinListFilters = Depends(),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: FatigueService = Depends(get_fatigue_service),
) -> SuccessResponse[FatigueCheckinListResponseData]:
    items = service.list_checkins(user_id=current_user.user_id, filters=filters)
    return SuccessResponse(
        data=FatigueCheckinListResponseData(items=items),
        meta={"count": len(items)},
    )


@router.get("/patterns", response_model=SuccessResponse[FatiguePatternListResponseData])
def list_fatigue_patterns(
    filters: FatiguePatternFilters = Depends(),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: FatigueService = Depends(get_fatigue_service),
) -> SuccessResponse[FatiguePatternListResponseData]:
    items = service.list_patterns(user_id=current_user.user_id, filters=filters)
    return SuccessResponse(
        data=FatiguePatternListResponseData(items=items),
        meta={"count": len(items)},
    )


@router.post("/patterns/recompute", response_model=SuccessResponse[FatiguePatternRecomputeResponseData], status_code=status.HTTP_202_ACCEPTED)
def recompute_fatigue_patterns(
    payload: FatiguePatternRecomputeRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: FatigueService = Depends(get_fatigue_service),
) -> SuccessResponse[FatiguePatternRecomputeResponseData]:
    job = service.recompute_patterns(user_id=current_user.user_id, payload=payload)
    return SuccessResponse(
        data=FatiguePatternRecomputeResponseData(job=job),
        message="Fatigue pattern recompute queued",
    )
