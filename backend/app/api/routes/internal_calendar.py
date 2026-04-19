from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, status

from app.core.db import get_db_connection
from app.core.security import AuthenticatedUser, get_current_user
from app.schemas.internal_calendar import (
    InternalCalendarCompleteRequest,
    InternalCalendarConfirmRequest,
    InternalCalendarDetailEnvelope,
    InternalCalendarListEnvelope,
    InternalCalendarListFilters,
    InternalCalendarMutationEnvelope,
    InternalCalendarRejectRequest,
    InternalCalendarRescheduleRequest,
    InternalCalendarSuggestEnvelope,
    InternalCalendarSuggestRequest,
)
from app.services.internal_calendar_service import InternalCalendarService

router = APIRouter(prefix="/internal-calendar")


def get_internal_calendar_service(
    connection: psycopg.Connection = Depends(get_db_connection),
) -> InternalCalendarService:
    return InternalCalendarService(connection)


@router.post("/suggest", response_model=InternalCalendarSuggestEnvelope, status_code=status.HTTP_201_CREATED)
def suggest_blocks(
    payload: InternalCalendarSuggestRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: InternalCalendarService = Depends(get_internal_calendar_service),
) -> InternalCalendarSuggestEnvelope:
    items = service.suggest_blocks(user_id=current_user.user_id, payload=payload)
    return InternalCalendarSuggestEnvelope(
        data={"items": items},
        message="Internal calendar suggestions created",
        meta={"count": len(items)},
    )


@router.get("", response_model=InternalCalendarListEnvelope)
def list_blocks(
    filters: InternalCalendarListFilters = Depends(),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: InternalCalendarService = Depends(get_internal_calendar_service),
) -> InternalCalendarListEnvelope:
    items = service.list_blocks(user_id=current_user.user_id, filters=filters)
    return InternalCalendarListEnvelope(
        data={"items": items},
        meta={"count": len(items), "next_cursor": None},
    )


@router.get("/{block_id}", response_model=InternalCalendarDetailEnvelope)
def get_block_detail(
    block_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: InternalCalendarService = Depends(get_internal_calendar_service),
) -> InternalCalendarDetailEnvelope:
    block, feedback = service.get_block_detail(user_id=current_user.user_id, block_id=block_id)
    return InternalCalendarDetailEnvelope(data={"block": block, "feedback": feedback})


@router.post("/{block_id}/confirm", response_model=InternalCalendarMutationEnvelope)
def confirm_block(
    block_id: str,
    payload: InternalCalendarConfirmRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: InternalCalendarService = Depends(get_internal_calendar_service),
) -> InternalCalendarMutationEnvelope:
    block = service.confirm_block(user_id=current_user.user_id, block_id=block_id, payload=payload)
    return InternalCalendarMutationEnvelope(
        data={"block": block, "feedback_recorded": True},
        message="Calendar block confirmed",
    )


@router.post("/{block_id}/reject", response_model=InternalCalendarMutationEnvelope)
def reject_block(
    block_id: str,
    payload: InternalCalendarRejectRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: InternalCalendarService = Depends(get_internal_calendar_service),
) -> InternalCalendarMutationEnvelope:
    block = service.reject_block(user_id=current_user.user_id, block_id=block_id, payload=payload)
    return InternalCalendarMutationEnvelope(
        data={"block": block, "feedback_recorded": True},
        message="Calendar block rejected",
    )


@router.post("/{block_id}/reschedule", response_model=InternalCalendarMutationEnvelope)
def reschedule_block(
    block_id: str,
    payload: InternalCalendarRescheduleRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: InternalCalendarService = Depends(get_internal_calendar_service),
) -> InternalCalendarMutationEnvelope:
    block = service.reschedule_block(user_id=current_user.user_id, block_id=block_id, payload=payload)
    return InternalCalendarMutationEnvelope(
        data={"block": block, "feedback_recorded": True},
        message="Calendar block rescheduled",
    )


@router.post("/{block_id}/complete", response_model=InternalCalendarMutationEnvelope)
def complete_block(
    block_id: str,
    payload: InternalCalendarCompleteRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: InternalCalendarService = Depends(get_internal_calendar_service),
) -> InternalCalendarMutationEnvelope:
    block, task = service.complete_block(user_id=current_user.user_id, block_id=block_id, payload=payload)
    return InternalCalendarMutationEnvelope(
        data={"block": block, "task": task},
        message="Calendar block completed",
    )
