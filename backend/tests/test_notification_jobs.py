from __future__ import annotations

import unittest
from datetime import UTC, datetime

from app.models.notification import NotificationChannel, NotificationModel, NotificationStatus
from app.services.notification_service import NotificationService
from app.services.telegram.telegram_dispatcher import TelegramDispatchPayload
from app.workers.jobs.notification_jobs import NotificationDeliveryWorker


class FakeNotificationRepository:
    def __init__(self, notification: NotificationModel) -> None:
        self.notification = notification
        self.locked = False

    def try_acquire_delivery_lock(self, *, notification_id: str) -> bool:
        if self.locked:
            return False
        self.locked = True
        return notification_id == self.notification.id

    def release_delivery_lock(self, *, notification_id: str) -> None:
        if notification_id == self.notification.id:
            self.locked = False

    def get_notification(self, *, notification_id: str, user_id: str | None = None) -> NotificationModel | None:
        if notification_id != self.notification.id:
            return None
        if user_id is not None and user_id != self.notification.user_id:
            return None
        return self.notification

    def mark_sent(self, *, notification_id: str, provider_message_id=None, sent_at=None, metadata_patch=None):
        if notification_id != self.notification.id or self.notification.status != NotificationStatus.QUEUED:
            return None
        self.notification.status = NotificationStatus.SENT
        self.notification.sent_at = sent_at
        self.notification.provider_message_id = provider_message_id
        if metadata_patch:
            self.notification.metadata_json.update(metadata_patch)
        return self.notification

    def mark_failed(self, *, notification_id: str, error_message: str, metadata_patch=None):
        if notification_id != self.notification.id or self.notification.status != NotificationStatus.QUEUED:
            return None
        self.notification.status = NotificationStatus.FAILED
        self.notification.metadata_json["last_error"] = error_message
        if metadata_patch:
            self.notification.metadata_json.update(metadata_patch)
        return self.notification

    def log_event(self, **kwargs):
        return "event-1"


class FakeDispatcher:
    def build_payload(self, notification: NotificationModel) -> TelegramDispatchPayload:
        return TelegramDispatchPayload(text=notification.body, reply_markup=None)


class FakeTelegramService:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.response = response if response is not None else {"ok": True, "result": {"message_id": 101}}
        self.error = error
        self.calls: list[dict] = []

    def send_linked_message(self, *, user_id: str, text: str, reply_markup=None, include_result: bool = False):
        self.calls.append(
            {
                "user_id": user_id,
                "text": text,
                "reply_markup": reply_markup,
                "include_result": include_result,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response if include_result else True


def build_notification(*, status: NotificationStatus = NotificationStatus.QUEUED) -> NotificationModel:
    return NotificationModel(
        id="notification-1",
        user_id="user-1",
        task_id="task-1",
        calendar_block_id=None,
        channel=NotificationChannel.TELEGRAM,
        title="Reminder",
        body="Check your plan",
        scheduled_for=datetime.now(UTC),
        sent_at=None,
        status=status,
        provider_message_id=None,
        metadata_json={"kind": "task_due_soon"},
        created_at=datetime.now(UTC),
    )


class NotificationJobTests(unittest.TestCase):
    def test_queued_telegram_notification_gets_delivered(self) -> None:
        repository = FakeNotificationRepository(build_notification())
        service = NotificationService(connection=None, repository=repository)
        worker = NotificationDeliveryWorker(
            repository=repository,
            service=service,
            dispatcher=FakeDispatcher(),
            telegram_service=FakeTelegramService(),
        )

        result = worker.deliver(notification_id="notification-1")

        self.assertTrue(result.sent)
        self.assertEqual(result.status, "sent")
        self.assertEqual(repository.notification.status, NotificationStatus.SENT)
        self.assertEqual(repository.notification.provider_message_id, "101")

    def test_already_sent_notification_is_skipped_safely(self) -> None:
        repository = FakeNotificationRepository(build_notification(status=NotificationStatus.SENT))
        telegram_service = FakeTelegramService()
        service = NotificationService(connection=None, repository=repository)
        worker = NotificationDeliveryWorker(
            repository=repository,
            service=service,
            dispatcher=FakeDispatcher(),
            telegram_service=telegram_service,
        )

        result = worker.deliver(notification_id="notification-1")

        self.assertFalse(result.sent)
        self.assertEqual(result.status, "already_sent")
        self.assertEqual(telegram_service.calls, [])

    def test_delivery_failure_marks_notification_failed(self) -> None:
        repository = FakeNotificationRepository(build_notification())
        service = NotificationService(connection=None, repository=repository)
        worker = NotificationDeliveryWorker(
            repository=repository,
            service=service,
            dispatcher=FakeDispatcher(),
            telegram_service=FakeTelegramService(error=RuntimeError("telegram down")),
        )

        result = worker.deliver(notification_id="notification-1")

        self.assertFalse(result.sent)
        self.assertEqual(result.status, "failed")
        self.assertEqual(repository.notification.status, NotificationStatus.FAILED)
        self.assertEqual(repository.notification.metadata_json["last_error"], "telegram down")


if __name__ == "__main__":
    unittest.main()
