from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime
from typing import Any
from urllib import error, parse, request

import psycopg
from fastapi import HTTPException, status

from app.core.config import Settings, get_settings
from app.models.telegram import ConnectorStatus, TelegramConnectorModel
from app.repositories.telegram import TelegramRepository
from app.schemas.telegram import TelegramConnectRequest, TelegramConnectionRead, TelegramEventRead, TelegramWebhookResult


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TelegramService:
    def __init__(self, connection: psycopg.Connection, settings: Settings | None = None) -> None:
        self.repository = TelegramRepository(connection)
        self.settings = settings or get_settings()

    def connect_bot(self, *, user_id: str, payload: TelegramConnectRequest) -> TelegramConnectionRead:
        token = payload.bot_token.strip()
        self._validate_token_shape(token)

        existing = self.repository.get_connector(user_id=user_id)
        existing_metadata = existing.metadata_json if existing else {}
        bot_profile = self._fetch_bot_profile(token) if self.settings.telegram_validate_bot_tokens else {}
        webhook_secret = existing_metadata.get("webhook_secret") or secrets.token_urlsafe(24)

        metadata = {
            **existing_metadata,
            "bot_token_hint": self._mask_token(token),
            "bot_username": bot_profile.get("username", existing_metadata.get("bot_username")),
            "bot_first_name": bot_profile.get("first_name", existing_metadata.get("bot_first_name")),
            "bot_id": bot_profile.get("id", existing_metadata.get("bot_id")),
            "webhook_secret": webhook_secret,
            "webhook_status": existing_metadata.get("webhook_status") or "not_configured",
            "telegram_user_id": existing_metadata.get("telegram_user_id"),
            "telegram_chat_id": existing_metadata.get("telegram_chat_id"),
            "last_event_at": existing_metadata.get("last_event_at"),
        }

        webhook_base_url = payload.webhook_base_url or self.settings.telegram_default_webhook_base_url
        if webhook_base_url:
            webhook_url = self._build_webhook_url(webhook_base_url, user_id)
            self._set_webhook(token, webhook_url, webhook_secret)
            metadata["webhook_url"] = webhook_url
            metadata["webhook_status"] = "configured"

        connector = self.repository.upsert_connector(
            user_id=user_id,
            # Do not persist Telegram bot tokens in plaintext in a column named
            # "access_token_encrypted" until real encryption/key management exists.
            bot_token=None,
            status=ConnectorStatus.CONNECTED,
            metadata=metadata,
        )
        self.repository.log_event(
            user_id=user_id,
            event_type="telegram_bot_connected",
            entity_id=connector.id,
            payload={
                "bot_username": metadata.get("bot_username"),
                "webhook_status": metadata.get("webhook_status"),
            },
        )
        return TelegramConnectionRead.from_model(connector)

    def get_connection(self, *, user_id: str) -> TelegramConnectionRead | None:
        connector = self.repository.get_connector(user_id=user_id)
        return TelegramConnectionRead.from_model(connector) if connector else None

    def list_events(self, *, user_id: str) -> list[TelegramEventRead]:
        events = self.repository.list_events(user_id=user_id)
        return [
            TelegramEventRead(
                id=str(record["id"]),
                event_type=record["event_type"],
                entity_type=record.get("entity_type"),
                entity_id=str(record["entity_id"]) if record.get("entity_id") else None,
                payload_json=record.get("payload_json") or {},
                created_at=record.get("created_at"),
            )
            for record in events
        ]

    def handle_webhook(self, *, user_id: str, update: dict[str, Any], secret: str | None) -> TelegramWebhookResult:
        connector = self.repository.get_connector(user_id=user_id)
        if connector is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Telegram connector not found")

        metadata = dict(connector.metadata_json or {})
        expected_secret = metadata.get("webhook_secret")
        if expected_secret and secret != expected_secret:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Telegram webhook secret")

        parsed_update = self._extract_update(update)
        metadata["telegram_user_id"] = parsed_update["telegram_user_id"] or metadata.get("telegram_user_id")
        metadata["telegram_chat_id"] = parsed_update["telegram_chat_id"] or metadata.get("telegram_chat_id")
        metadata["last_event_at"] = _utcnow().isoformat()

        updated_connector = self.repository.update_connector_metadata(
            connector_id=connector.id,
            metadata=metadata,
            status=ConnectorStatus.CONNECTED,
        )
        event_id = self.repository.log_event(
            user_id=user_id,
            event_type=f"telegram_{parsed_update['update_type']}_received",
            entity_id=updated_connector.id,
            payload=parsed_update,
        )

        return TelegramWebhookResult(
            linked=metadata.get("telegram_chat_id") is not None,
            update_type=parsed_update["update_type"],
            event_id=event_id or "",
        )

    def _extract_update(self, update: dict[str, Any]) -> dict[str, Any]:
        if "message" in update:
            message = update["message"] or {}
            sender = message.get("from") or {}
            chat = message.get("chat") or {}
            return {
                "update_type": "message",
                "telegram_user_id": sender.get("id"),
                "telegram_chat_id": chat.get("id"),
                "text": message.get("text"),
                "raw_update_id": update.get("update_id"),
            }

        if "callback_query" in update:
            callback = update["callback_query"] or {}
            sender = callback.get("from") or {}
            message = callback.get("message") or {}
            chat = message.get("chat") or {}
            return {
                "update_type": "callback_query",
                "telegram_user_id": sender.get("id"),
                "telegram_chat_id": chat.get("id"),
                "text": message.get("text"),
                "callback_data": callback.get("data"),
                "raw_update_id": update.get("update_id"),
            }

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported Telegram update type")

    def _validate_token_shape(self, token: str) -> None:
        if ":" not in token:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Telegram bot token format is invalid")
        left, right = token.split(":", 1)
        if not left.isdigit() or len(right) < 20:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Telegram bot token format is invalid")

    def _mask_token(self, token: str) -> str:
        head, _, tail = token.partition(":")
        if len(tail) <= 6:
            return f"{head}:***"
        return f"{head}:{tail[:3]}...{tail[-3:]}"

    def _fetch_bot_profile(self, token: str) -> dict[str, Any]:
        payload = self._telegram_request(token, "getMe")
        if not payload.get("ok"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telegram rejected the provided bot token")
        return payload.get("result") or {}

    def _set_webhook(self, token: str, webhook_url: str, secret: str) -> None:
        payload = self._telegram_request(
            token,
            "setWebhook",
            {
                "url": webhook_url,
                "secret_token": secret,
                "allowed_updates": ["message", "callback_query"],
            },
        )
        if not payload.get("ok"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telegram webhook registration failed")

    def _telegram_request(self, token: str, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"https://api.telegram.org/bot{token}/{method}"
        body = None
        headers = {"Content-Type": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")

        req = request.Request(url, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Telegram API error: {detail or exc.reason}") from exc
        except error.URLError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Telegram API is unavailable") from exc

    def _build_webhook_url(self, webhook_base_url: str, user_id: str) -> str:
        normalized_base = webhook_base_url.rstrip("/")
        encoded_user_id = parse.quote(user_id, safe="")
        return f"{normalized_base}{self.settings.api_prefix}/telegram/webhook/{encoded_user_id}"
