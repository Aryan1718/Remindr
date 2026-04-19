from __future__ import annotations

import json
import logging
import secrets
import ssl
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any
from urllib import error, parse, request
from zoneinfo import ZoneInfo

import psycopg
from fastapi import HTTPException, status

from app.core.config import Settings, get_settings
from app.models.telegram import ConnectorStatus, TelegramConnectorModel
from app.repositories.telegram import TelegramRepository
from app.repositories.users import UserRepository
from app.schemas.telegram import TelegramConnectRequest, TelegramConnectionRead, TelegramEventRead, TelegramWebhookResult
from app.services.agent_service import AgentService, NormalizedTelegramInbound, TelegramAgentReply

logger = logging.getLogger("app.services.telegram")


def _utcnow() -> datetime:
    return datetime.now(UTC)


@lru_cache(maxsize=1)
def _build_ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


ONBOARDING_STEP_ORDER = (
    "full_name",
    "timezone",
    "wake_time",
    "sleep_time",
    "preferred_response_style",
)

ONBOARDING_PROMPTS = {
    "full_name": "What should I call you?",
    "timezone": "What timezone should I use for you? Choose one of the options below.",
    "wake_time": "What time do you usually wake up? Reply in 24-hour HH:MM format.",
    "sleep_time": "What time do you usually go to sleep? Reply in 24-hour HH:MM format.",
    "preferred_response_style": "How should I respond by default? Choose one of the options below.",
}

TIMEZONE_OPTIONS = {
    "Pacific Time": "America/Los_Angeles",
    "Eastern Time": "America/New_York",
    "Central Time": "America/Chicago",
    "UTC": "Etc/UTC",
    "Central European Time": "Europe/Paris",
    "Singapore Time": "Asia/Singapore",
}

RESPONSE_STYLE_OPTIONS = {
    "Aggressive": "aggressive",
    "Balanced": "balanced",
    "Gentle": "gentle",
}

CONFIRMATION_PENDING = "pending"
CONFIRMATION_CONFIRMED = "confirmed"
CONFIRMATION_DECLINED = "declined"


class TelegramService:
    def __init__(
        self,
        connection: psycopg.Connection | None,
        settings: Settings | None = None,
        repository: TelegramRepository | None = None,
        user_repository: UserRepository | None = None,
        agent_service: AgentService | None = None,
    ) -> None:
        self.repository = repository or TelegramRepository(connection)
        self.user_repository = user_repository or UserRepository(connection)
        self.settings = settings or get_settings()
        self.agent_service = agent_service or (AgentService(connection, settings=self.settings) if connection is not None else None)

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
            "telegram_user_id": None,
            "telegram_chat_id": None,
            "pending_telegram_user_id": None,
            "pending_telegram_chat_id": None,
            "last_event_at": existing_metadata.get("last_event_at"),
            "confirmation_status": CONFIRMATION_PENDING,
            "confirmation_requested_at": _utcnow().isoformat(),
            "confirmation_confirmed_at": None,
        }

        webhook_base_url = payload.webhook_base_url or self.settings.telegram_default_webhook_base_url
        if not webhook_base_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Telegram webhook base URL is not configured on the backend.",
            )

        webhook_url = self._build_webhook_url(webhook_base_url, user_id)
        self._set_webhook(token, webhook_url, webhook_secret)
        metadata["webhook_url"] = webhook_url
        metadata["webhook_status"] = "configured"

        connector = self.repository.upsert_connector(
            user_id=user_id,
            # MVP: keep the bot token in the existing connector token column so
            # the webhook flow can send outbound replies. This should be
            # replaced with real encryption/key management.
            bot_token=token,
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
                "confirmation_status": metadata.get("confirmation_status"),
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
            logger.warning(
                "Rejected Telegram webhook for user_id=%s: connector not found",
                user_id,
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Telegram connector not found")

        metadata = dict(connector.metadata_json or {})
        expected_secret = metadata.get("webhook_secret")
        if expected_secret and secret != expected_secret:
            logger.warning(
                "Rejected Telegram webhook for user_id=%s connector_id=%s: webhook secret mismatch expected=%s received=%s",
                user_id,
                connector.id,
                self._redact_secret(expected_secret),
                self._redact_secret(secret),
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Telegram webhook secret")

        parsed_update = self._extract_update(update)
        if self.repository.has_processed_update(
            user_id=user_id,
            entity_id=connector.id,
            raw_update_id=parsed_update.get("raw_update_id"),
        ):
            return TelegramWebhookResult(
                linked=metadata.get("telegram_chat_id") is not None,
                update_type=parsed_update["update_type"],
                event_id="",
            )
        onboarding_active = self._is_onboarding_active(user_id) if self._is_confirmed(metadata) else False
        metadata["last_event_at"] = _utcnow().isoformat()
        if self._is_confirmed(metadata):
            metadata["telegram_user_id"] = parsed_update["telegram_user_id"] or metadata.get("telegram_user_id")
            metadata["telegram_chat_id"] = parsed_update["telegram_chat_id"] or metadata.get("telegram_chat_id")
            status_value = ConnectorStatus.CONNECTED
        else:
            metadata["pending_telegram_user_id"] = parsed_update["telegram_user_id"] or metadata.get("pending_telegram_user_id")
            metadata["pending_telegram_chat_id"] = parsed_update["telegram_chat_id"] or metadata.get("pending_telegram_chat_id")
            status_value = connector.status

        updated_connector = self.repository.update_connector_metadata(
            connector_id=connector.id,
            metadata=metadata,
            status=status_value,
        )
        self._maybe_progress_onboarding(
            user_id=user_id,
            connector=updated_connector,
            parsed_update=parsed_update,
        )
        event_id = self.repository.log_event(
            user_id=user_id,
            event_type=f"telegram_{parsed_update['update_type']}_received",
            entity_id=updated_connector.id,
            payload=parsed_update,
        )
        self._maybe_handle_agent_interaction(
            user_id=user_id,
            connector=updated_connector,
            metadata=metadata,
            parsed_update=parsed_update,
            onboarding_active=onboarding_active,
        )

        return TelegramWebhookResult(
            linked=metadata.get("telegram_chat_id") is not None,
            update_type=parsed_update["update_type"],
            event_id=event_id or "",
        )

    def _maybe_progress_onboarding(
        self,
        *,
        user_id: str,
        connector: TelegramConnectorModel,
        parsed_update: dict[str, Any],
    ) -> None:
        if parsed_update["update_type"] != "message":
            return

        message_text = (parsed_update.get("text") or "").strip()
        chat_id = parsed_update.get("telegram_chat_id")
        if not message_text or chat_id is None:
            return

        connector_metadata = dict(connector.metadata_json or {})
        if not self._is_confirmed(connector_metadata):
            self._handle_confirmation_message(
                user_id=user_id,
                connector=connector,
                parsed_update=parsed_update,
                message_text=message_text,
            )
            return

        preferences = self.user_repository.get_preferences(user_id) or self.user_repository.create_preferences(user_id)
        profile_json = dict(preferences.profile_json or {})
        onboarding_state = dict(profile_json.get("telegram_onboarding") or {})

        if message_text.lower() == "/start":
            next_step = self._resolve_next_step(preferences)
            if next_step is None:
                self._send_message(
                    connector=connector,
                    chat_id=chat_id,
                    text="You are already onboarded. Send /start anytime if you want to check the bot connection.",
                )
                return

            profile_json["telegram_onboarding"] = {
                "active": True,
                "step": next_step,
                "started_at": onboarding_state.get("started_at") or _utcnow().isoformat(),
                "last_prompt_at": _utcnow().isoformat(),
            }
            self.user_repository.update_preferences(user_id, values={"profile_json": profile_json})
            self._send_message(
                connector=connector,
                chat_id=chat_id,
                text=ONBOARDING_PROMPTS[next_step],
                reply_markup=self._reply_markup_for_step(next_step),
            )
            return

        if not onboarding_state.get("active"):
            return

        current_step = onboarding_state.get("step")
        if current_step not in ONBOARDING_PROMPTS:
            next_step = self._resolve_next_step(preferences)
            if next_step is None:
                return
            current_step = next_step

        try:
            self._apply_onboarding_answer(
                user_id=user_id,
                preferences=preferences,
                step=current_step,
                answer=message_text,
            )
        except HTTPException as exc:
            self._send_message(
                connector=connector,
                chat_id=chat_id,
                text=exc.detail,
                reply_markup=self._reply_markup_for_step(current_step),
            )
            return

        refreshed_preferences = self.user_repository.get_preferences(user_id) or preferences
        next_step = self._resolve_next_step(refreshed_preferences)
        refreshed_profile = dict(refreshed_preferences.profile_json or {})

        if next_step is None:
            refreshed_profile["telegram_onboarding"] = {
                "active": False,
                "step": None,
                "completed_at": _utcnow().isoformat(),
            }
            self.user_repository.update_preferences(
                user_id,
                values={
                    "onboarding_completed": True,
                    "profile_json": refreshed_profile,
                },
            )
            self.repository.log_event(
                user_id=user_id,
                event_type="telegram_onboarding_completed",
                entity_id=connector.id,
                payload={"telegram_chat_id": chat_id},
            )
            self._send_message(
                connector=connector,
                chat_id=chat_id,
                text="Onboarding complete. I’ve saved your basics and I’m ready for the next step.",
                reply_markup={"remove_keyboard": True},
            )
            return

        refreshed_profile["telegram_onboarding"] = {
            "active": True,
            "step": next_step,
            "started_at": onboarding_state.get("started_at") or _utcnow().isoformat(),
            "last_prompt_at": _utcnow().isoformat(),
        }
        self.user_repository.update_preferences(user_id, values={"profile_json": refreshed_profile})
        self._send_message(
            connector=connector,
            chat_id=chat_id,
            text=ONBOARDING_PROMPTS[next_step],
            reply_markup=self._reply_markup_for_step(next_step),
        )

    def _apply_onboarding_answer(
        self,
        *,
        user_id: str,
        preferences,
        step: str,
        answer: str,
    ) -> None:
        normalized = answer.strip()
        if step == "full_name":
            if len(normalized) < 2:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Please send a name with at least 2 characters.")
            user = self.user_repository.get_user(user_id)
            self.user_repository.update_user(
                user_id,
                email=user.email if user else None,
                full_name=normalized,
                timezone=user.timezone if user else None,
            )
            return

        if step == "timezone":
            normalized_timezone = TIMEZONE_OPTIONS.get(normalized, normalized)
            try:
                ZoneInfo(normalized_timezone)
            except Exception as exc:  # pragma: no cover - ZoneInfo raises implementation-specific errors
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="That timezone is invalid. Choose one of the listed timezone options.",
                ) from exc
            user = self.user_repository.get_user(user_id)
            self.user_repository.update_user(
                user_id,
                email=user.email if user else None,
                full_name=user.full_name if user else None,
                timezone=normalized_timezone,
            )
            profile_json = dict(preferences.profile_json or {})
            profile_json["telegram_onboarding_timezone_confirmed"] = True
            self.user_repository.update_preferences(user_id, values={"profile_json": profile_json})
            return

        if step in {"wake_time", "sleep_time"}:
            parsed = self._parse_time_value(normalized)
            self.user_repository.update_preferences(user_id, values={step: parsed})
            return

        if step == "preferred_response_style":
            lowered = RESPONSE_STYLE_OPTIONS.get(normalized, normalized.lower())
            if lowered not in set(RESPONSE_STYLE_OPTIONS.values()):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Choose Aggressive, Balanced, or Gentle from the options below.",
                )
            self.user_repository.update_preferences(
                user_id,
                values={"preferred_response_style": lowered},
            )
            return

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported onboarding step")

    def _handle_confirmation_message(
        self,
        *,
        user_id: str,
        connector: TelegramConnectorModel,
        parsed_update: dict[str, Any],
        message_text: str,
    ) -> None:
        chat_id = parsed_update.get("telegram_chat_id")
        telegram_user_id = parsed_update.get("telegram_user_id")
        if chat_id is None:
            return

        normalized = message_text.strip().lower()
        metadata = dict(connector.metadata_json or {})
        metadata["pending_telegram_chat_id"] = chat_id
        metadata["pending_telegram_user_id"] = telegram_user_id

        if normalized == "/start":
            metadata["confirmation_status"] = CONFIRMATION_PENDING
            self.repository.update_connector_metadata(
                connector_id=connector.id,
                metadata=metadata,
                status=connector.status,
            )
            self.repository.log_event(
                user_id=user_id,
                event_type="telegram_confirmation_requested",
                entity_id=connector.id,
                payload={"telegram_chat_id": chat_id},
            )
            self._send_message(
                connector=connector,
                chat_id=chat_id,
                text="Thank you for confirming. I verified the bot token. Do you want to link this Telegram chat to Remindr?",
                reply_markup=self._reply_markup_for_step("connect_confirmation"),
            )
            return

        if normalized in {"yes", "connect", "confirm"}:
            metadata["confirmation_status"] = CONFIRMATION_CONFIRMED
            metadata["confirmation_confirmed_at"] = _utcnow().isoformat()
            metadata["telegram_chat_id"] = chat_id
            metadata["telegram_user_id"] = telegram_user_id
            metadata["pending_telegram_chat_id"] = None
            metadata["pending_telegram_user_id"] = None
            updated_connector = self.repository.update_connector_metadata(
                connector_id=connector.id,
                metadata=metadata,
                status=ConnectorStatus.CONNECTED,
            )
            self.repository.log_event(
                user_id=user_id,
                event_type="telegram_connection_confirmed",
                entity_id=updated_connector.id,
                payload={"telegram_chat_id": chat_id},
            )
            self._send_message(
                connector=updated_connector,
                chat_id=chat_id,
                text="Thank you for confirming. Your Telegram chat is now connected to Remindr.",
                reply_markup={"remove_keyboard": True},
            )
            return

        if normalized in {"no", "cancel", "decline"}:
            metadata["confirmation_status"] = CONFIRMATION_DECLINED
            metadata["confirmation_confirmed_at"] = None
            metadata["telegram_chat_id"] = None
            metadata["telegram_user_id"] = None
            metadata["pending_telegram_chat_id"] = None
            metadata["pending_telegram_user_id"] = None
            updated_connector = self.repository.update_connector_metadata(
                connector_id=connector.id,
                metadata=metadata,
                status=ConnectorStatus.REVOKED,
            )
            self.repository.log_event(
                user_id=user_id,
                event_type="telegram_connection_declined",
                entity_id=updated_connector.id,
                payload={"telegram_chat_id": chat_id},
            )
            self._send_message(
                connector=updated_connector,
                chat_id=chat_id,
                text="Okay. I did not connect this Telegram chat to Remindr.",
                reply_markup={"remove_keyboard": True},
            )
            return

        self.repository.update_connector_metadata(
            connector_id=connector.id,
            metadata=metadata,
            status=connector.status,
        )
        self._send_message(
            connector=connector,
            chat_id=chat_id,
            text="Reply Yes to connect this chat to Remindr, or No to cancel.",
            reply_markup=self._reply_markup_for_step("connect_confirmation"),
        )


    def _resolve_next_step(self, preferences) -> str | None:
        user = self.user_repository.get_user(preferences.user_id)
        profile_json = dict(preferences.profile_json or {})
        for step in ONBOARDING_STEP_ORDER:
            if step == "full_name" and not (user.full_name if user else None):
                return step
            if step == "timezone" and not profile_json.get("telegram_onboarding_timezone_confirmed"):
                return step
            if step == "wake_time" and not preferences.wake_time:
                return step
            if step == "sleep_time" and not preferences.sleep_time:
                return step
            if step == "preferred_response_style" and not preferences.preferred_response_style:
                return step
        return None

    def _is_confirmed(self, metadata: dict[str, Any]) -> bool:
        return metadata.get("confirmation_status") == CONFIRMATION_CONFIRMED and metadata.get("telegram_chat_id") is not None

    def _is_onboarding_active(self, user_id: str) -> bool:
        preferences = self.user_repository.get_preferences(user_id)
        if preferences is None:
            return False
        profile_json = dict(preferences.profile_json or {})
        onboarding_state = dict(profile_json.get("telegram_onboarding") or {})
        return bool(onboarding_state.get("active"))

    def _parse_time_value(self, value: str) -> str:
        parts = value.split(":")
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Please reply in HH:MM format, for example 07:30.",
            )
        hours = int(parts[0])
        minutes = int(parts[1])
        if hours not in range(24) or minutes not in range(60):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Please reply with a valid 24-hour time like 07:30.",
            )
        return f"{hours:02d}:{minutes:02d}"

    def _send_message(
        self,
        *,
        connector: TelegramConnectorModel,
        chat_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> None:
        token = connector.access_token_encrypted
        if not token:
            return
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        self._telegram_request(
            token,
            "sendMessage",
            payload,
        )

    def send_linked_message(
        self,
        *,
        user_id: str,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        include_result: bool = False,
    ) -> bool | dict[str, Any]:
        connector = self.repository.get_connector(user_id=user_id)
        if connector is None:
            return False
        metadata = dict(connector.metadata_json or {})
        if not self._is_confirmed(metadata):
            return False
        chat_id = metadata.get("telegram_chat_id")
        if not isinstance(chat_id, int):
            return False
        token = connector.access_token_encrypted
        if not token:
            return False
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        response = self._telegram_request(
            token,
            "sendMessage",
            payload,
        )
        self.repository.log_event(
            user_id=user_id,
            event_type="telegram_outbound_message_sent",
            entity_id=connector.id,
            payload={"text": text},
        )
        if include_result:
            return response
        return True

    def _answer_callback_query(self, *, connector: TelegramConnectorModel, callback_query_id: str, text: str | None = None) -> None:
        token = connector.access_token_encrypted
        if not token:
            return
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        self._telegram_request(
            token,
            "answerCallbackQuery",
            payload,
        )

    def _reply_markup_for_step(self, step: str) -> dict[str, Any] | None:
        if step == "connect_confirmation":
            return {
                "keyboard": [
                    [{"text": "Yes"}, {"text": "No"}],
                ],
                "resize_keyboard": True,
                "one_time_keyboard": True,
            }
        if step == "timezone":
            return {
                "keyboard": [
                    [{"text": "Pacific Time"}, {"text": "Eastern Time"}],
                    [{"text": "Central Time"}, {"text": "UTC"}],
                    [{"text": "Central European Time"}, {"text": "Singapore Time"}],
                ],
                "resize_keyboard": True,
                "one_time_keyboard": True,
            }
        if step == "preferred_response_style":
            return {
                "keyboard": [
                    [{"text": "Aggressive"}, {"text": "Balanced"}, {"text": "Gentle"}],
                ],
                "resize_keyboard": True,
                "one_time_keyboard": True,
            }
        return {"remove_keyboard": True}

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
                "callback_query_id": callback.get("id"),
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

    def _redact_secret(self, value: str | None) -> str:
        if not value:
            return "<missing>"
        if len(value) <= 8:
            return "***"
        return f"{value[:4]}...{value[-4:]}"

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
                "drop_pending_updates": True,
            },
            use_query_params=True,
        )
        if not payload.get("ok"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telegram webhook registration failed")

    def _telegram_request(
        self,
        token: str,
        method: str,
        payload: dict[str, Any] | None = None,
        *,
        use_query_params: bool = False,
    ) -> dict[str, Any]:
        url = f"https://api.telegram.org/bot{token}/{method}"
        body = None
        headers = {"Content-Type": "application/json"}
        if payload is not None and use_query_params:
            encoded_payload = parse.urlencode(
                {
                    key: json.dumps(value) if isinstance(value, (list, dict)) else value
                    for key, value in payload.items()
                }
            )
            url = f"{url}?{encoded_payload}"
        elif payload is not None:
            body = json.dumps(payload).encode("utf-8")

        request_method = "GET" if use_query_params or payload is None else "POST"
        req = request.Request(url, data=body, headers=headers, method=request_method)
        try:
            with request.urlopen(req, timeout=10, context=_build_ssl_context()) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Telegram API error: {detail or exc.reason}") from exc
        except error.URLError as exc:
            reason = str(exc.reason).strip() if getattr(exc, "reason", None) else "unavailable"
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Telegram API is unavailable: {reason}",
            ) from exc

    def _build_webhook_url(self, webhook_base_url: str, user_id: str) -> str:
        normalized_base = webhook_base_url.rstrip("/")
        encoded_user_id = parse.quote(user_id, safe="")
        return f"{normalized_base}{self.settings.api_prefix}/telegram/webhook/{encoded_user_id}"

    def _maybe_handle_agent_interaction(
        self,
        *,
        user_id: str,
        connector: TelegramConnectorModel,
        metadata: dict[str, Any],
        parsed_update: dict[str, Any],
        onboarding_active: bool,
    ) -> None:
        if self.agent_service is None or not self._is_confirmed(metadata):
            return

        if parsed_update["update_type"] == "message":
            message_text = (parsed_update.get("text") or "").strip()
            if not message_text or message_text.lower() == "/start" or onboarding_active:
                return
        elif parsed_update["update_type"] != "callback_query":
            return

        reply = self.agent_service.handle_telegram_inbound(
            user_id=user_id,
            inbound=NormalizedTelegramInbound(
                update_type=parsed_update["update_type"],
                text=parsed_update.get("text"),
                callback_data=parsed_update.get("callback_data"),
                callback_query_id=parsed_update.get("callback_query_id"),
                telegram_chat_id=parsed_update.get("telegram_chat_id"),
                telegram_user_id=parsed_update.get("telegram_user_id"),
            ),
        )
        if reply is None:
            return
        self._dispatch_agent_reply(
            user_id=user_id,
            connector=connector,
            parsed_update=parsed_update,
            reply=reply,
        )

    def _dispatch_agent_reply(
        self,
        *,
        user_id: str,
        connector: TelegramConnectorModel,
        parsed_update: dict[str, Any],
        reply: TelegramAgentReply,
    ) -> None:
        chat_id = parsed_update.get("telegram_chat_id")
        if isinstance(chat_id, int):
            self._send_message(
                connector=connector,
                chat_id=chat_id,
                text=reply.text,
                reply_markup=reply.reply_markup,
            )
        callback_query_id = parsed_update.get("callback_query_id")
        if isinstance(callback_query_id, str) and callback_query_id:
            self._answer_callback_query(
                connector=connector,
                callback_query_id=callback_query_id,
                text=reply.callback_notice,
            )
        self.repository.log_event(
            user_id=user_id,
            event_type="telegram_agent_reply_sent",
            entity_id=connector.id,
            payload={
                "intent": reply.intent,
                "text": reply.text,
            },
        )
