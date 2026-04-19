from __future__ import annotations

from typing import Any

import psycopg
from fastapi import APIRouter, Depends, Header, status

from app.core.db import get_db_connection
from app.core.security import AuthenticatedUser, get_current_user
from app.schemas.telegram import (
    TelegramConnectionEnvelope,
    TelegramEventListEnvelope,
    TelegramWebhookResult,
    TelegramConnectRequest,
)
from app.services.telegram_service import TelegramService

router = APIRouter(prefix="/telegram")


def get_telegram_service(connection: psycopg.Connection = Depends(get_db_connection)) -> TelegramService:
    return TelegramService(connection)


@router.post("/bots/connect", response_model=TelegramConnectionEnvelope, status_code=status.HTTP_201_CREATED)
def connect_telegram_bot(
    payload: TelegramConnectRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: TelegramService = Depends(get_telegram_service),
) -> TelegramConnectionEnvelope:
    connection = service.connect_bot(user_id=current_user.user_id, payload=payload)
    return TelegramConnectionEnvelope(data={"connection": connection}, message="Telegram bot connected")


@router.get("/bots/me", response_model=TelegramConnectionEnvelope)
def get_telegram_connection(
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: TelegramService = Depends(get_telegram_service),
) -> TelegramConnectionEnvelope:
    connection = service.get_connection(user_id=current_user.user_id)
    return TelegramConnectionEnvelope(data={"connection": connection})


@router.get("/bots/me/events", response_model=TelegramEventListEnvelope)
def list_telegram_events(
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: TelegramService = Depends(get_telegram_service),
) -> TelegramEventListEnvelope:
    events = service.list_events(user_id=current_user.user_id)
    return TelegramEventListEnvelope(data={"items": events}, meta={"count": len(events)})


@router.post("/webhook/{user_id}", response_model=TelegramConnectionEnvelope)
def handle_telegram_webhook(
    user_id: str,
    update: dict[str, Any],
    service: TelegramService = Depends(get_telegram_service),
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> TelegramConnectionEnvelope:
    result: TelegramWebhookResult = service.handle_webhook(
        user_id=user_id,
        update=update,
        secret=x_telegram_bot_api_secret_token,
    )
    return TelegramConnectionEnvelope(data={"result": result})
