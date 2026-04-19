from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from app.models.notification import NotificationChannel, NotificationModel, NotificationStatus
from app.schemas.notification import NotificationCreateRequest, NotificationListFilters
from app.services.notification_service import NotificationService


class InMemoryNotificationRepository:
    def __init__(self) -> None:
        self.notifications: dict[str, NotificationModel] = {}
        self.logged_events: list[dict] = []

    def create_notification(
        self,
        *,
        user_id: str,
        task_id: str | None,
        calendar_block_id: str | None,
        channel: NotificationChannel,
        title: str | None,
        body: str,
        scheduled_for: datetime | None,
        status: NotificationStatus,
        metadata_json: dict | None = None,
    ) -> NotificationModel:
        notification = NotificationModel(
            id=f"notification-{len(self.notifications) + 1}",
            user_id=user_id,
            task_id=task_id,
            calendar_block_id=calendar_block_id,
            channel=channel,
            title=title,
            body=body,
            scheduled_for=scheduled_for,
            sent_at=None,
            status=status,
            provider_message_id=None,
            metadata_json=metadata_json or {},
            created_at=datetime.now(UTC),
        )
        self.notifications[notification.id] = notification
        return notification

    def list_notifications(
        self,
        *,
        user_id: str,
        status: NotificationStatus | None = None,
        channel: NotificationChannel | None = None,
        scheduled_before: datetime | None = None,
        scheduled_after: datetime | None = None,
        limit: int = 50,
    ) -> list[NotificationModel]:
        items = [item for item in self.notifications.values() if item.user_id == user_id]
        if status is not None:
            items = [item for item in items if item.status == status]
        if channel is not None:
            items = [item for item in items if item.channel == channel]
        if scheduled_before is not None:
            items = [item for item in items if item.scheduled_for and item.scheduled_for <= scheduled_before]
        if scheduled_after is not None:
            items = [item for item in items if item.scheduled_for is None or item.scheduled_for >= scheduled_after]
        items.sort(key=lambda item: item.created_at or datetime.min.replace(tzinfo=UTC), reverse=True)
        return items[:limit]

    def get_notification(self, *, notification_id: str, user_id: str | None = None) -> NotificationModel | None:
        notification = self.notifications.get(notification_id)
        if notification is None:
            return None
        if user_id is not None and notification.user_id != user_id:
            return None
        return notification

    def mark_sent(
        self,
        *,
        notification_id: str,
        provider_message_id: str | None = None,
        sent_at: datetime | None = None,
        metadata_patch: dict | None = None,
    ) -> NotificationModel | None:
        notification = self.notifications.get(notification_id)
        if notification is None or notification.status != NotificationStatus.QUEUED:
            return None
        notification.status = NotificationStatus.SENT
        notification.sent_at = sent_at
        notification.provider_message_id = provider_message_id
        if metadata_patch:
            notification.metadata_json.update(metadata_patch)
        return notification

    def mark_failed(
        self,
        *,
        notification_id: str,
        error_message: str,
        metadata_patch: dict | None = None,
    ) -> NotificationModel | None:
        notification = self.notifications.get(notification_id)
        if notification is None or notification.status != NotificationStatus.QUEUED:
            return None
        notification.status = NotificationStatus.FAILED
        notification.metadata_json["last_error"] = error_message
        if metadata_patch:
            notification.metadata_json.update(metadata_patch)
        return notification

    def dismiss_notification(self, *, notification_id: str, user_id: str) -> NotificationModel | None:
        notification = self.get_notification(notification_id=notification_id, user_id=user_id)
        if notification is None:
            return None
        notification.status = NotificationStatus.DISMISSED
        return notification

    def log_event(self, *, user_id: str, event_type: str, notification_id: str, payload=None) -> str:
        self.logged_events.append(
            {
                "user_id": user_id,
                "event_type": event_type,
                "notification_id": notification_id,
                "payload": payload or {},
            }
        )
        return f"event-{len(self.logged_events)}"


class NotificationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryNotificationRepository()
        self.service = NotificationService(connection=None, repository=self.repository)
        self.service.enqueue_notification_delivery = MagicMock(
            return_value=type("Job", (), {"job_id": "job-1", "status": "queued"})()
        )

    def test_create_queued_notification(self) -> None:
        notification = self.service.create_notification(
            user_id="user-1",
            title="Reminder",
            body="Check your plan",
            scheduled_for=datetime.now(UTC) + timedelta(minutes=10),
            metadata_json={"kind": "generic_reminder"},
        )

        self.assertEqual(notification.channel, NotificationChannel.TELEGRAM)
        self.assertEqual(notification.status, NotificationStatus.QUEUED)
        self.assertEqual(notification.metadata_json["kind"], "generic_reminder")

    def test_enqueue_delivery_calls_worker_helper(self) -> None:
        result = self.service.enqueue_delivery(notification_id="notification-1")

        self.assertEqual(result.job_id, "job-1")
        self.service.enqueue_notification_delivery.assert_called_once_with(notification_id="notification-1")

    def test_mark_sent_updates_status_and_logs_event(self) -> None:
        notification = self.repository.create_notification(
            user_id="user-1",
            task_id=None,
            calendar_block_id=None,
            channel=NotificationChannel.TELEGRAM,
            title="Reminder",
            body="Check your plan",
            scheduled_for=None,
            status=NotificationStatus.QUEUED,
            metadata_json={},
        )

        updated = self.service.mark_sent(notification_id=notification.id, provider_message_id="55")

        assert updated is not None
        self.assertEqual(updated.status, NotificationStatus.SENT)
        self.assertEqual(updated.provider_message_id, "55")
        self.assertEqual(self.repository.logged_events[-1]["event_type"], "telegram_notification_sent")

    def test_mark_failed_updates_status_and_logs_event(self) -> None:
        notification = self.repository.create_notification(
            user_id="user-1",
            task_id=None,
            calendar_block_id=None,
            channel=NotificationChannel.TELEGRAM,
            title="Reminder",
            body="Check your plan",
            scheduled_for=None,
            status=NotificationStatus.QUEUED,
            metadata_json={},
        )

        updated = self.service.mark_failed(notification_id=notification.id, error_message="link missing")

        assert updated is not None
        self.assertEqual(updated.status, NotificationStatus.FAILED)
        self.assertEqual(updated.metadata_json["last_error"], "link missing")
        self.assertEqual(self.repository.logged_events[-1]["event_type"], "telegram_notification_failed")

    def test_create_test_notification_creates_and_enqueues(self) -> None:
        notification, job = self.service.create_test_notification(
            user_id="user-1",
            payload=NotificationCreateRequest(title="Test", body="This is a test notification"),
        )

        self.assertEqual(notification.status, NotificationStatus.QUEUED)
        self.assertEqual(notification.metadata_json["source"], "notifications.test")
        self.assertEqual(job.job_id, "job-1")

    def test_list_notifications_is_owner_scoped(self) -> None:
        self.repository.create_notification(
            user_id="user-1",
            task_id=None,
            calendar_block_id=None,
            channel=NotificationChannel.TELEGRAM,
            title=None,
            body="User one",
            scheduled_for=None,
            status=NotificationStatus.QUEUED,
            metadata_json={},
        )
        self.repository.create_notification(
            user_id="user-2",
            task_id=None,
            calendar_block_id=None,
            channel=NotificationChannel.TELEGRAM,
            title=None,
            body="User two",
            scheduled_for=None,
            status=NotificationStatus.QUEUED,
            metadata_json={},
        )

        items = self.service.list_notifications(user_id="user-1", filters=NotificationListFilters())

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].body, "User one")


if __name__ == "__main__":
    unittest.main()
