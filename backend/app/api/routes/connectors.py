from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import RedirectResponse

from app.core.db import get_db_connection
from app.core.security import AuthenticatedUser, get_current_user
from app.schemas.connector import (
    ConnectorConnectRequest,
    ConnectorEnvelope,
    ConnectorListEnvelope,
    ConnectorSyncRequest,
)
from app.services.connector_service import ConnectorService

router = APIRouter(prefix="/connectors")


def get_connector_service(connection: psycopg.Connection = Depends(get_db_connection)) -> ConnectorService:
    return ConnectorService(connection)


@router.get("", response_model=ConnectorListEnvelope)
def list_connectors(
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ConnectorService = Depends(get_connector_service),
) -> ConnectorListEnvelope:
    items = service.list_connectors(user_id=current_user.user_id)
    return ConnectorListEnvelope(data={"items": items}, meta={"count": len(items)})


@router.post("/google-calendar/connect", response_model=ConnectorEnvelope, status_code=status.HTTP_201_CREATED)
def connect_google_calendar(
    payload: ConnectorConnectRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ConnectorService = Depends(get_connector_service),
) -> ConnectorEnvelope:
    connector = service.connect_google_calendar(user_id=current_user.user_id, payload=payload)
    return ConnectorEnvelope(data={"connector": connector}, message="Google Calendar connector connected")


@router.post("/google-calendar/oauth/start", response_model=ConnectorEnvelope)
def start_google_calendar_oauth(
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ConnectorService = Depends(get_connector_service),
) -> ConnectorEnvelope:
    result = service.build_google_oauth_start(
        user_id=current_user.user_id,
        user_email=current_user.email,
    )
    return ConnectorEnvelope(data=result.model_dump(), message="Google OAuth URL created")


@router.get("/google-calendar/oauth/callback", include_in_schema=False)
def handle_google_calendar_oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    service: ConnectorService = Depends(get_connector_service),
) -> RedirectResponse:
    if error:
        redirect_url = service._build_frontend_callback_url(status_value="error", reason=error)  # noqa: SLF001
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    if not code or not state:
        redirect_url = service._build_frontend_callback_url(  # noqa: SLF001
            status_value="error",
            reason="Missing Google OAuth callback parameters",
        )
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    redirect_url = service.complete_google_oauth_callback(code=code, state=state)
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


@router.post("/{connector_id}/sync", response_model=ConnectorEnvelope, status_code=status.HTTP_202_ACCEPTED)
def trigger_connector_sync(
    connector_id: str,
    payload: ConnectorSyncRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ConnectorService = Depends(get_connector_service),
) -> ConnectorEnvelope:
    result = service.trigger_sync(user_id=current_user.user_id, connector_id=connector_id, payload=payload)
    return ConnectorEnvelope(data=result.model_dump(), message="Connector sync queued")
