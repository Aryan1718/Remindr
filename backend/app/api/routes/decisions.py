from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends

from app.core.db import get_db_connection
from app.core.security import AuthenticatedUser, get_current_user
from app.schemas.decision import (
    DayPlanEnvelope,
    DecisionEnvelope,
    DecisionNextBestActionRequest,
    DecisionPlanDayRequest,
    DecisionQueryRequest,
)
from app.services.decision_service import DecisionService

router = APIRouter(prefix="/decision")


def get_decision_service(
    connection: psycopg.Connection = Depends(get_db_connection),
) -> DecisionService:
    return DecisionService(connection)


@router.post("/query", response_model=DecisionEnvelope)
def query_decision(
    payload: DecisionQueryRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: DecisionService = Depends(get_decision_service),
) -> DecisionEnvelope:
    response = service.query(user_id=current_user.user_id, payload=payload)
    return DecisionEnvelope(data=response)


@router.post("/next-best-action", response_model=DecisionEnvelope)
def next_best_action(
    payload: DecisionNextBestActionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: DecisionService = Depends(get_decision_service),
) -> DecisionEnvelope:
    response = service.next_best_action(user_id=current_user.user_id, payload=payload)
    return DecisionEnvelope(data=response)


@router.post("/plan-day", response_model=DayPlanEnvelope)
def plan_day(
    payload: DecisionPlanDayRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: DecisionService = Depends(get_decision_service),
) -> DayPlanEnvelope:
    response = service.plan_day(user_id=current_user.user_id, payload=payload)
    return DayPlanEnvelope(data=response)
