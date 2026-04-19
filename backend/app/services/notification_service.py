from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import psycopg
from fastapi import HTTPException, status

from app.models.notification import NotificationChannel, NotificationStatus
from app.models.task import TaskModel
from app.models.internal_calendar import InternalCalendarBlockModel
from app.repositories.notifications import NotificationRepository
from app.schemas.notification import NotificationCreateRequest, NotificationListFilters, NotificationRead
from app.workers.rq import enqueue_notification_delivery

logger = logging.getLogger("app.services.notifications")


class NotificationService:
    def __init__(
        self,
        connection: psycopg.Connection | None = None,
        *,
        repository: NotificationRepository | None = None,
    ) -> None:
        self.repository = repository or self._require_repo(connection)
        self.enqueue_notification_delivery = enqueue_notification_delivery

    def create_notification(
        self,
        *,
        user_id: str,
        body: str,
        channel: NotificationChannel = NotificationChannel.TELEGRAM,
        title: str | None = None,
        task_id: str | None = None,
        calendar_block_id: str | None = None,
        scheduled_for: datetime | None = None,
        metadata_json: dict[str, Any] | None = None,
        status: NotificationStatus = NotificationStatus.QUEUED,
    ) -> NotificationRead:
        notification = self.repository.create_notification(
            user_id=user_id,
            task_id=task_id,
            calendar_block_id=calendar_block_id,
            channel=channel,
            title=title,
            body=body,
            scheduled_for=scheduled_for,
            status=status,
            metadata_json=metadata_json or {},
        )
        return NotificationRead.from_model(notification)

    def queue_telegram_notification(
        self,
        *,
        user_id: str,
        body: str,
        title: str | None = None,
        task_id: str | None = None,
        calendar_block_id: str | None = None,
        scheduled_for: datetime | None = None,
        metadata_json: dict[str, Any] | None = None,
        enqueue: bool = True,
    ) -> tuple[NotificationRead, Any | None]:
        notification = self.create_notification(
            user_id=user_id,
            task_id=task_id,
            calendar_block_id=calendar_block_id,
            channel=NotificationChannel.TELEGRAM,
            title=title,
            body=body,
            scheduled_for=scheduled_for,
            status=NotificationStatus.QUEUED,
            metadata_json=metadata_json or {},
        )
        job = self.enqueue_delivery(notification_id=notification.id) if enqueue else None
        return notification, job

    def enqueue_delivery(self, *, notification_id: str) -> Any:
        logger.info("Enqueuing notification delivery notification_id=%s", notification_id)
        return self.enqueue_notification_delivery(notification_id=notification_id)

    def mark_sent(
        self,
        *,
        notification_id: str,
        provider_message_id: str | None = None,
        metadata_patch: dict[str, Any] | None = None,
    ) -> NotificationRead | None:
        notification = self.repository.mark_sent(
            notification_id=notification_id,
            provider_message_id=provider_message_id,
            sent_at=datetime.now(UTC),
            metadata_patch=metadata_patch,
        )
        if notification is None:
            return None
        self.repository.log_event(
            user_id=notification.user_id,
            event_type="telegram_notification_sent",
            notification_id=notification.id,
            payload={"channel": notification.channel.value},
        )
        return NotificationRead.from_model(notification)

    def mark_failed(
        self,
        *,
        notification_id: str,
        error_message: str,
        metadata_patch: dict[str, Any] | None = None,
    ) -> NotificationRead | None:
        notification = self.repository.mark_failed(
            notification_id=notification_id,
            error_message=error_message,
            metadata_patch=metadata_patch,
        )
        if notification is None:
            return None
        self.repository.log_event(
            user_id=notification.user_id,
            event_type="telegram_notification_failed",
            notification_id=notification.id,
            payload={"channel": notification.channel.value, "error": error_message},
        )
        return NotificationRead.from_model(notification)

    def list_notifications(self, *, user_id: str, filters: NotificationListFilters) -> list[NotificationRead]:
        notifications = self.repository.list_notifications(
            user_id=user_id,
            status=filters.status,
            channel=filters.channel,
            scheduled_before=filters.scheduled_before,
            scheduled_after=filters.scheduled_after,
            limit=filters.limit,
        )
        return [NotificationRead.from_model(item) for item in notifications]

    def dismiss_notification(self, *, user_id: str, notification_id: str) -> NotificationRead:
        notification = self.repository.dismiss_notification(notification_id=notification_id, user_id=user_id)
        if notification is None:
            existing = self.repository.get_notification(notification_id=notification_id, user_id=user_id)
            if existing is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
            return NotificationRead.from_model(existing)
        self.repository.log_event(
            user_id=user_id,
            event_type="notification_dismissed",
            notification_id=notification.id,
            payload={"status": notification.status.value},
        )
        return NotificationRead.from_model(notification)

    def create_test_notification(
        self,
        *,
        user_id: str,
        payload: NotificationCreateRequest,
    ) -> tuple[NotificationRead, Any | None]:
        if payload.channel != NotificationChannel.TELEGRAM:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only Telegram test notifications are currently supported",
            )
        metadata_json = {
            "kind": "generic_reminder",
            "source": "notifications.test",
        }
        return self.queue_telegram_notification(
            user_id=user_id,
            title=payload.title,
            body=payload.body,
            metadata_json=metadata_json,
            enqueue=True,
        )

    def queue_internal_calendar_suggestion_reminder(
        self,
        *,
        block: InternalCalendarBlockModel,
        timezone_name: str | None = None,
    ) -> tuple[NotificationRead, Any | None]:
        return self.queue_telegram_notification(
            user_id=block.user_id,
            task_id=block.task_id,
            calendar_block_id=block.id,
            title="Calendar reminder",
            body=f"{block.title} is coming up soon. Confirm it, move it, or reject it.",
            scheduled_for=block.starts_at,
            metadata_json={
                "kind": "internal_calendar_suggestion",
                "calendar_block_id": block.id,
                "block_title": block.title,
                "starts_at": block.starts_at.isoformat(),
                "timezone": timezone_name,
            },
        )

    def queue_task_due_soon_alert(
        self,
        *,
        task: TaskModel,
        timezone_name: str | None = None,
    ) -> tuple[NotificationRead, Any | None]:
        return self.queue_telegram_notification(
            user_id=task.user_id,
            task_id=task.id,
            title="Task due soon",
            body=f"{task.title} needs attention soon.",
            scheduled_for=task.due_at,
            metadata_json={
                "kind": "task_due_soon",
                "task_id": task.id,
                "task_title": task.title,
                "due_at": task.due_at.isoformat() if task.due_at else None,
                "timezone": timezone_name,
            },
        )

    def queue_fatigue_check_prompt(
        self,
        *,
        user_id: str,
        body: str = "How are you feeling right now on a 0-5 scale?",
    ) -> tuple[NotificationRead, Any | None]:
        return self.queue_telegram_notification(
            user_id=user_id,
            title="Quick fatigue check",
            body=body,
            metadata_json={"kind": "fatigue_check_prompt"},
        )

    @staticmethod
    def _require_repo(connection: psycopg.Connection | None) -> NotificationRepository:
        if connection is None:
            raise RuntimeError("NotificationService requires a database connection or repository")
        return NotificationRepository(connection)
