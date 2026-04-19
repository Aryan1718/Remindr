from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.models.notification import NotificationChannel, NotificationStatus
from app.repositories.notifications import NotificationRepository
from app.services.notification_service import NotificationService
from app.services.telegram.telegram_dispatcher import TelegramNotificationDispatcher
from app.services.telegram_service import TelegramService

logger = logging.getLogger("app.workers.notifications")


@dataclass(slots=True)
class NotificationDeliveryResult:
    notification_id: str
    status: str
    sent: bool
    detail: str | None = None


class NotificationDeliveryWorker:
    def __init__(
        self,
        *,
        repository,
        service: NotificationService,
        dispatcher: TelegramNotificationDispatcher,
        telegram_service: TelegramService,
    ) -> None:
        self.repository = repository
        self.service = service
        self.dispatcher = dispatcher
        self.telegram_service = telegram_service

    def deliver(self, *, notification_id: str) -> NotificationDeliveryResult:
        lock_acquired = False
        try:
            lock_acquired = self.repository.try_acquire_delivery_lock(notification_id=notification_id)
            if not lock_acquired:
                logger.info("Notification delivery skipped; lock busy notification_id=%s", notification_id)
                return NotificationDeliveryResult(notification_id=notification_id, status="locked", sent=False)

            notification = self.repository.get_notification(notification_id=notification_id)
            if notification is None:
                return NotificationDeliveryResult(
                    notification_id=notification_id,
                    status="missing",
                    sent=False,
                    detail="Notification not found",
                )
            if notification.status == NotificationStatus.SENT:
                logger.info("Notification already sent notification_id=%s", notification_id)
                return NotificationDeliveryResult(notification_id=notification_id, status="already_sent", sent=False)
            if notification.status != NotificationStatus.QUEUED:
                logger.info(
                    "Notification delivery skipped due to status notification_id=%s status=%s",
                    notification_id,
                    notification.status.value,
                )
                return NotificationDeliveryResult(
                    notification_id=notification_id,
                    status="ineligible",
                    sent=False,
                    detail=notification.status.value,
                )
            if notification.channel != NotificationChannel.TELEGRAM:
                logger.info(
                    "Notification delivery skipped due to channel notification_id=%s channel=%s",
                    notification_id,
                    notification.channel.value,
                )
                return NotificationDeliveryResult(
                    notification_id=notification_id,
                    status="unsupported_channel",
                    sent=False,
                    detail=notification.channel.value,
                )

            dispatch_payload = self.dispatcher.build_payload(notification)
            provider_response = self.telegram_service.send_linked_message(
                user_id=notification.user_id,
                text=dispatch_payload.text,
                reply_markup=dispatch_payload.reply_markup,
                include_result=True,
            )
            if not provider_response or not provider_response.get("ok", True):
                detail = "Telegram linked send returned false"
                self.service.mark_failed(
                    notification_id=notification.id,
                    error_message=detail,
                    metadata_patch={"delivery_channel": notification.channel.value},
                )
                return NotificationDeliveryResult(
                    notification_id=notification.id,
                    status="failed",
                    sent=False,
                    detail=detail,
                )

            provider_message_id = self._extract_provider_message_id(provider_response)
            self.service.mark_sent(
                notification_id=notification.id,
                provider_message_id=provider_message_id,
                metadata_patch={"delivery_channel": notification.channel.value},
            )
            logger.info("Notification delivered notification_id=%s", notification.id)
            return NotificationDeliveryResult(
                notification_id=notification.id,
                status=NotificationStatus.SENT.value,
                sent=True,
                detail=provider_message_id,
            )
        except Exception as exc:
            logger.exception("Notification delivery failed notification_id=%s", notification_id)
            self.service.mark_failed(notification_id=notification_id, error_message=str(exc))
            return NotificationDeliveryResult(
                notification_id=notification_id,
                status=NotificationStatus.FAILED.value,
                sent=False,
                detail=str(exc),
            )
        finally:
            if lock_acquired:
                self.repository.release_delivery_lock(notification_id=notification_id)

    @staticmethod
    def _extract_provider_message_id(provider_response: Any) -> str | None:
        if not isinstance(provider_response, dict):
            return None
        result = provider_response.get("result")
        if not isinstance(result, dict):
            return None
        message_id = result.get("message_id")
        return str(message_id) if message_id is not None else None


def deliver_notification_job(*, database_url: str, notification_id: str) -> NotificationDeliveryResult:
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        repository = NotificationRepository(connection)
        service = NotificationService(connection=connection, repository=repository)
        dispatcher = TelegramNotificationDispatcher()
        telegram_service = TelegramService(connection)
        worker = NotificationDeliveryWorker(
            repository=repository,
            service=service,
            dispatcher=dispatcher,
            telegram_service=telegram_service,
        )
        return worker.deliver(notification_id=notification_id)
