from __future__ import annotations

import unittest
from datetime import UTC, datetime

from app.models.telegram import ConnectorStatus, TelegramConnectorModel
from app.models.user import UserModel, UserPreferencesModel
from app.services.agent_service import TelegramAgentReply
from app.services.telegram_service import TelegramService


class InMemoryTelegramRepository:
    def __init__(self) -> None:
        self.connector = TelegramConnectorModel(
            id="connector-1",
            user_id="user-1",
            provider="telegram",
            status=ConnectorStatus.CONNECTED,
            account_email="telegram-bot",
            access_token_encrypted="123456:telegram-token-for-tests",
            metadata_json={"webhook_secret": "secret-token"},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.logged_events: list[dict] = []

    def get_connector(self, *, user_id: str) -> TelegramConnectorModel | None:
        return self.connector if self.connector.user_id == user_id else None

    def update_connector_metadata(
        self,
        *,
        connector_id: str,
        metadata: dict,
        status: ConnectorStatus | None = None,
    ) -> TelegramConnectorModel:
        self.connector.metadata_json = dict(metadata)
        if status is not None:
            self.connector.status = status
        self.connector.updated_at = datetime.now(UTC)
        return self.connector

    def log_event(self, *, user_id: str, event_type: str, entity_id: str | None, payload=None) -> str:
        self.logged_events.append(
            {
                "user_id": user_id,
                "event_type": event_type,
                "entity_id": entity_id,
                "payload": payload or {},
            }
        )
        return f"event-{len(self.logged_events)}"

    def list_events(self, *, user_id: str, limit: int = 50) -> list[dict]:
        return []

    def upsert_connector(
        self,
        *,
        user_id: str,
        bot_token: str | None,
        status: ConnectorStatus,
        metadata: dict,
        account_email: str | None = "telegram-bot",
    ) -> TelegramConnectorModel:
        self.connector.user_id = user_id
        self.connector.access_token_encrypted = bot_token
        self.connector.status = status
        self.connector.account_email = account_email
        self.connector.metadata_json = dict(metadata)
        self.connector.updated_at = datetime.now(UTC)
        return self.connector


class InMemoryUserRepository:
    def __init__(self) -> None:
        self.user = UserModel(
            id="user-1",
            auth_user_id="auth-1",
            email="test@example.com",
            full_name=None,
            timezone="America/Los_Angeles",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.preferences = UserPreferencesModel(
            id="pref-1",
            user_id="user-1",
            profile_json={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def get_user(self, user_id: str) -> UserModel | None:
        return self.user if self.user.id == user_id else None

    def update_user(self, user_id: str, *, email: str | None, full_name: str | None, timezone: str | None) -> UserModel:
        if email is not None:
            self.user.email = email
        if full_name is not None:
            self.user.full_name = full_name
        if timezone is not None:
            self.user.timezone = timezone
        self.user.updated_at = datetime.now(UTC)
        return self.user

    def get_preferences(self, user_id: str) -> UserPreferencesModel | None:
        return self.preferences if self.preferences.user_id == user_id else None

    def create_preferences(self, user_id: str) -> UserPreferencesModel:
        self.preferences.user_id = user_id
        return self.preferences

    def update_preferences(self, user_id: str, *, values: dict[str, object]) -> UserPreferencesModel:
        for key, value in values.items():
            if key == "profile_json":
                merged = dict(self.preferences.profile_json or {})
                merged.update(value if isinstance(value, dict) else {})
                self.preferences.profile_json = merged
                continue
            setattr(self.preferences, key, value)
        self.preferences.updated_at = datetime.now(UTC)
        return self.preferences


class RecordingTelegramService(TelegramService):
    def __init__(
        self,
        repository: InMemoryTelegramRepository,
        user_repository: InMemoryUserRepository,
        *,
        agent_service=None,
    ) -> None:
        super().__init__(
            connection=None,
            repository=repository,
            user_repository=user_repository,
            agent_service=agent_service,
        )
        self.sent_messages: list[dict] = []
        self.telegram_requests: list[dict] = []

    def _telegram_request(
        self,
        token: str,
        method: str,
        payload: dict | None = None,
        *,
        use_query_params: bool = False,
    ) -> dict:
        self.telegram_requests.append(
            {
                "token": token,
                "method": method,
                "payload": payload or {},
                "use_query_params": use_query_params,
            }
        )
        if method == "sendMessage":
            self.sent_messages.append({"token": token, "payload": payload or {}})
            return {"ok": True, "result": {}}
        if method == "getMe":
            return {
                "ok": True,
                "result": {
                    "id": 123456,
                    "username": "fatigue_killer_bot",
                    "first_name": "Fatigue Killer",
                },
            }
        return {"ok": True, "result": True}


class FakeAgentService:
    def __init__(self, reply: TelegramAgentReply | None = None) -> None:
        self.reply = reply
        self.calls: list[dict] = []

    def handle_telegram_inbound(self, *, user_id: str, inbound) -> TelegramAgentReply | None:
        self.calls.append({"user_id": user_id, "inbound": inbound})
        return self.reply


class TelegramServiceTests(unittest.TestCase):
    def test_connect_bot_registers_webhook_with_query_params(self) -> None:
        repository = InMemoryTelegramRepository()
        user_repository = InMemoryUserRepository()
        service = RecordingTelegramService(repository, user_repository)

        connection = service.connect_bot(
            user_id="user-1",
            payload=type(
                "Payload",
                (),
                {
                    "bot_token": "123456:telegram-token-for-tests",
                    "webhook_base_url": "https://example.trycloudflare.com",
                },
            )(),
        )

        self.assertEqual(connection.webhook_status, "configured")
        self.assertIsNone(connection.telegram_chat_id)
        set_webhook_request = next(request for request in service.telegram_requests if request["method"] == "setWebhook")
        self.assertTrue(set_webhook_request["use_query_params"])
        self.assertEqual(
            set_webhook_request["payload"]["url"],
            "https://example.trycloudflare.com/api/v1/telegram/webhook/user-1",
        )

    def test_start_message_requests_confirmation_before_onboarding(self) -> None:
        repository = InMemoryTelegramRepository()
        user_repository = InMemoryUserRepository()
        service = RecordingTelegramService(repository, user_repository)

        result = service.handle_webhook(
            user_id="user-1",
            update={
                "update_id": 1,
                "message": {
                    "text": "/start",
                    "from": {"id": 555},
                    "chat": {"id": 777},
                },
            },
            secret="secret-token",
        )

        self.assertFalse(result.linked)
        self.assertNotIn("telegram_onboarding", user_repository.preferences.profile_json)
        self.assertEqual(
            service.sent_messages[-1]["payload"]["text"],
            "Thank you for confirming. I verified the bot token. Do you want to link this Telegram chat to Remindr?",
        )
        self.assertEqual(service.sent_messages[-1]["payload"]["reply_markup"]["keyboard"][0][0]["text"], "Yes")

    def test_confirmation_yes_then_onboarding_completes(self) -> None:
        repository = InMemoryTelegramRepository()
        user_repository = InMemoryUserRepository()
        service = RecordingTelegramService(repository, user_repository)

        def send_message(text: str) -> None:
            service.handle_webhook(
                user_id="user-1",
                update={
                    "update_id": len(service.sent_messages) + 1,
                    "message": {
                        "text": text,
                        "from": {"id": 555},
                        "chat": {"id": 777},
                    },
                },
                secret="secret-token",
            )

        send_message("/start")
        send_message("Yes")
        self.assertEqual(repository.connector.metadata_json["confirmation_status"], "confirmed")
        self.assertEqual(repository.connector.metadata_json["telegram_chat_id"], 777)
        self.assertEqual(service.sent_messages[-1]["payload"]["text"], "Thank you for confirming. Your Telegram chat is now connected to Remindr.")

        send_message("/start")
        self.assertEqual(user_repository.preferences.profile_json["telegram_onboarding"]["step"], "full_name")
        send_message("Varun")
        self.assertEqual(user_repository.user.full_name, "Varun")
        self.assertEqual(user_repository.preferences.profile_json["telegram_onboarding"]["step"], "timezone")

        send_message("Eastern Time")
        self.assertEqual(user_repository.user.timezone, "America/New_York")
        self.assertTrue(user_repository.preferences.profile_json["telegram_onboarding_timezone_confirmed"])
        self.assertEqual(user_repository.preferences.profile_json["telegram_onboarding"]["step"], "wake_time")

        send_message("07:30")
        self.assertEqual(user_repository.preferences.wake_time, "07:30")
        self.assertEqual(user_repository.preferences.profile_json["telegram_onboarding"]["step"], "sleep_time")

        send_message("23:15")
        self.assertEqual(user_repository.preferences.sleep_time, "23:15")
        self.assertEqual(user_repository.preferences.profile_json["telegram_onboarding"]["step"], "preferred_response_style")

        send_message("Balanced")
        self.assertEqual(user_repository.preferences.preferred_response_style, "balanced")
        self.assertTrue(user_repository.preferences.onboarding_completed)
        self.assertFalse(user_repository.preferences.profile_json["telegram_onboarding"]["active"])
        self.assertEqual(
            service.sent_messages[-1]["payload"]["text"],
            "Onboarding complete. I’ve saved your basics and I’m ready for the next step.",
        )

    def test_decline_keeps_connector_unlinked(self) -> None:
        repository = InMemoryTelegramRepository()
        user_repository = InMemoryUserRepository()
        service = RecordingTelegramService(repository, user_repository)

        service.handle_webhook(
            user_id="user-1",
            update={
                "update_id": 1,
                "message": {
                    "text": "/start",
                    "from": {"id": 555},
                    "chat": {"id": 777},
                },
            },
            secret="secret-token",
        )
        service.handle_webhook(
            user_id="user-1",
            update={
                "update_id": 2,
                "message": {
                    "text": "No",
                    "from": {"id": 555},
                    "chat": {"id": 777},
                },
            },
            secret="secret-token",
        )

        self.assertEqual(repository.connector.status, ConnectorStatus.REVOKED)
        self.assertIsNone(repository.connector.metadata_json["telegram_chat_id"])
        self.assertEqual(service.sent_messages[-1]["payload"]["text"], "Okay. I did not connect this Telegram chat to Remindr.")

    def test_option_steps_include_reply_keyboards(self) -> None:
        repository = InMemoryTelegramRepository()
        user_repository = InMemoryUserRepository()
        service = RecordingTelegramService(repository, user_repository)

        service.handle_webhook(
            user_id="user-1",
            update={
                "update_id": 1,
                "message": {
                    "text": "/start",
                    "from": {"id": 555},
                    "chat": {"id": 777},
                },
            },
            secret="secret-token",
        )
        service.handle_webhook(
            user_id="user-1",
            update={
                "update_id": 2,
                "message": {
                    "text": "Yes",
                    "from": {"id": 555},
                    "chat": {"id": 777},
                },
            },
            secret="secret-token",
        )
        service.handle_webhook(
            user_id="user-1",
            update={
                "update_id": 3,
                "message": {
                    "text": "/start",
                    "from": {"id": 555},
                    "chat": {"id": 777},
                },
            },
            secret="secret-token",
        )
        service.handle_webhook(
            user_id="user-1",
            update={
                "update_id": 4,
                "message": {
                    "text": "Varun",
                    "from": {"id": 555},
                    "chat": {"id": 777},
                },
            },
            secret="secret-token",
        )

        timezone_prompt = service.sent_messages[-1]["payload"]
        self.assertEqual(timezone_prompt["text"], "What timezone should I use for you? Choose one of the options below.")
        self.assertIn("reply_markup", timezone_prompt)
        self.assertEqual(timezone_prompt["reply_markup"]["keyboard"][0][0]["text"], "Pacific Time")

    def test_confirmed_non_onboarding_message_routes_to_agent(self) -> None:
        repository = InMemoryTelegramRepository()
        repository.connector.metadata_json.update(
            {
                "confirmation_status": "confirmed",
                "telegram_chat_id": 777,
                "telegram_user_id": 555,
            }
        )
        user_repository = InMemoryUserRepository()
        user_repository.preferences.profile_json = {"telegram_onboarding": {"active": False}}
        agent_service = FakeAgentService(
            TelegramAgentReply(
                text="First: Finish resume bullets.",
                intent="decision_query",
                reply_markup={"inline_keyboard": [[{"text": "Done", "callback_data": "task:done:task-1"}]]},
            )
        )
        service = RecordingTelegramService(repository, user_repository, agent_service=agent_service)

        service.handle_webhook(
            user_id="user-1",
            update={
                "update_id": 9,
                "message": {
                    "text": "What should I do first tonight?",
                    "from": {"id": 555},
                    "chat": {"id": 777},
                },
            },
            secret="secret-token",
        )

        self.assertEqual(agent_service.calls[0]["user_id"], "user-1")
        self.assertEqual(agent_service.calls[0]["inbound"].text, "What should I do first tonight?")
        self.assertEqual(service.sent_messages[-1]["payload"]["text"], "First: Finish resume bullets.")
        self.assertEqual(service.sent_messages[-1]["payload"]["reply_markup"]["inline_keyboard"][0][0]["text"], "Done")

    def test_callback_query_routes_to_agent_and_answers_callback(self) -> None:
        repository = InMemoryTelegramRepository()
        repository.connector.metadata_json.update(
            {
                "confirmation_status": "confirmed",
                "telegram_chat_id": 777,
                "telegram_user_id": 555,
            }
        )
        user_repository = InMemoryUserRepository()
        agent_service = FakeAgentService(
            TelegramAgentReply(
                text="Marked done: Finish resume bullets.",
                intent="task_complete",
                callback_notice="Task marked done.",
            )
        )
        service = RecordingTelegramService(repository, user_repository, agent_service=agent_service)

        service.handle_webhook(
            user_id="user-1",
            update={
                "update_id": 10,
                "callback_query": {
                    "id": "callback-1",
                    "data": "task:done:task-1",
                    "from": {"id": 555},
                    "message": {
                        "text": "Finish resume bullets",
                        "chat": {"id": 777},
                    },
                },
            },
            secret="secret-token",
        )

        self.assertEqual(agent_service.calls[0]["inbound"].callback_data, "task:done:task-1")
        self.assertEqual(service.sent_messages[-1]["payload"]["text"], "Marked done: Finish resume bullets.")
        answer_request = next(request for request in service.telegram_requests if request["method"] == "answerCallbackQuery")
        self.assertEqual(answer_request["payload"]["callback_query_id"], "callback-1")
        self.assertEqual(answer_request["payload"]["text"], "Task marked done.")

    def test_send_linked_message_uses_existing_outbound_flow(self) -> None:
        repository = InMemoryTelegramRepository()
        repository.connector.metadata_json.update(
            {
                "confirmation_status": "confirmed",
                "telegram_chat_id": 777,
                "telegram_user_id": 555,
            }
        )
        user_repository = InMemoryUserRepository()
        service = RecordingTelegramService(repository, user_repository)

        sent = service.send_linked_message(
            user_id="user-1",
            text="You have a good 45-minute window right now.",
        )

        self.assertTrue(sent)
        self.assertEqual(service.sent_messages[-1]["payload"]["chat_id"], 777)
        self.assertEqual(service.sent_messages[-1]["payload"]["text"], "You have a good 45-minute window right now.")


if __name__ == "__main__":
    unittest.main()
