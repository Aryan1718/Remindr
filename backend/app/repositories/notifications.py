from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg import sql
from psycopg.errors import UndefinedTable

from app.models.notification import NotificationChannel, NotificationModel, NotificationStatus

logger = logging.getLogger("app.repositories.notifications")

NOTIFICATION_COLUMNS = """
    id,
    user_id,
    task_id,
    calendar_block_id,
    channel,
    title,
    body,
    scheduled_for,
    sent_at,
    status,
    provider_message_id,
    metadata_json,
    created_at
"""


class NotificationRepository:
    def __init__(self, connection: psycopg.Connection) -> None:
        self.connection = connection

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
        metadata_json: dict[str, Any] | None = None,
    ) -> NotificationModel:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                insert into notifications (
                    user_id,
                    task_id,
                    calendar_block_id,
                    channel,
                    title,
                    body,
                    scheduled_for,
                    status,
                    metadata_json
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                returning {NOTIFICATION_COLUMNS}
                """,
                (
                    user_id,
                    task_id,
                    calendar_block_id,
                    channel.value,
                    title,
                    body,
                    scheduled_for,
                    status.value,
                    json.dumps(metadata_json or {}),
                ),
            )
            record = cursor.fetchone()

        self.connection.commit()
        return NotificationModel.from_record(record)

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
        clauses: list[sql.Composed] = [sql.SQL("user_id = %s")]
        params: list[Any] = [user_id]

        if status is not None:
            clauses.append(sql.SQL("status = %s"))
            params.append(status.value)
        if channel is not None:
            clauses.append(sql.SQL("channel = %s"))
            params.append(channel.value)
        if scheduled_before is not None:
            clauses.append(sql.SQL("scheduled_for <= %s"))
            params.append(scheduled_before)
        if scheduled_after is not None:
            clauses.append(sql.SQL("(scheduled_for is null or scheduled_for >= %s)"))
            params.append(scheduled_after)

        query = sql.SQL(
            """
            select {columns}
            from notifications
            where {where_clause}
            order by coalesce(scheduled_for, created_at) desc, created_at desc
            limit %s
            """
        ).format(
            columns=sql.SQL(NOTIFICATION_COLUMNS),
            where_clause=sql.SQL(" and ").join(clauses),
        )
        params.append(limit)

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            records = cursor.fetchall()

        return [NotificationModel.from_record(record) for record in records]

    def get_notification(
        self,
        *,
        notification_id: str,
        user_id: str | None = None,
    ) -> NotificationModel | None:
        clauses = ["id = %s"]
        params: list[Any] = [notification_id]
        if user_id is not None:
            clauses.append("user_id = %s")
            params.append(user_id)

        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                select {NOTIFICATION_COLUMNS}
                from notifications
                where {' and '.join(clauses)}
                limit 1
                """,
                params,
            )
            record = cursor.fetchone()

        return NotificationModel.from_record(record) if record else None

    def mark_sent(
        self,
        *,
        notification_id: str,
        provider_message_id: str | None = None,
        sent_at: datetime | None = None,
        metadata_patch: dict[str, Any] | None = None,
    ) -> NotificationModel | None:
        return self._update_status(
            notification_id=notification_id,
            from_statuses=[NotificationStatus.QUEUED],
            to_status=NotificationStatus.SENT,
            sent_at=sent_at or datetime.now(UTC),
            provider_message_id=provider_message_id,
            metadata_patch=metadata_patch,
        )

    def mark_failed(
        self,
        *,
        notification_id: str,
        error_message: str,
        metadata_patch: dict[str, Any] | None = None,
    ) -> NotificationModel | None:
        patch = {
            "last_error": error_message,
            "last_error_at": datetime.now(UTC).isoformat(),
        }
        if metadata_patch:
            patch.update(metadata_patch)
        return self._update_status(
            notification_id=notification_id,
            from_statuses=[NotificationStatus.QUEUED],
            to_status=NotificationStatus.FAILED,
            metadata_patch=patch,
        )

    def dismiss_notification(self, *, notification_id: str, user_id: str) -> NotificationModel | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                update notifications
                set status = %s
                where id = %s
                  and user_id = %s
                  and status <> %s
                returning {NOTIFICATION_COLUMNS}
                """,
                (
                    NotificationStatus.DISMISSED.value,
                    notification_id,
                    user_id,
                    NotificationStatus.DISMISSED.value,
                ),
            )
            record = cursor.fetchone()

        self.connection.commit()
        return NotificationModel.from_record(record) if record else None

    def try_acquire_delivery_lock(self, *, notification_id: str) -> bool:
        with self.connection.cursor() as cursor:
            cursor.execute("select pg_try_advisory_lock(hashtext(%s)) as acquired", (notification_id,))
            record = cursor.fetchone()
        return bool(record and record["acquired"])

    def release_delivery_lock(self, *, notification_id: str) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute("select pg_advisory_unlock(hashtext(%s))", (notification_id,))

    def log_event(
        self,
        *,
        user_id: str,
        event_type: str,
        notification_id: str,
        payload: Mapping[str, Any] | None = None,
    ) -> str | None:
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    insert into interaction_events (
                        user_id,
                        event_type,
                        entity_type,
                        entity_id,
                        payload_json
                    )
                    values (%s, %s, 'notification', %s, %s::jsonb)
                    returning id
                    """,
                    (
                        user_id,
                        event_type,
                        notification_id,
                        json.dumps(dict(payload or {})),
                    ),
                )
                record = cursor.fetchone()
            self.connection.commit()
            return str(record["id"]) if record else None
        except UndefinedTable:
            self.connection.rollback()
            logger.warning("interaction_events table not found; skipped %s event", event_type)
            return None

    def _update_status(
        self,
        *,
        notification_id: str,
        from_statuses: list[NotificationStatus],
        to_status: NotificationStatus,
        sent_at: datetime | None = None,
        provider_message_id: str | None = None,
        metadata_patch: dict[str, Any] | None = None,
    ) -> NotificationModel | None:
        existing = self.get_notification(notification_id=notification_id)
        if existing is None or existing.status not in set(from_statuses):
            return None

        metadata_json = dict(existing.metadata_json or {})
        if metadata_patch:
            metadata_json.update(metadata_patch)

        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                update notifications
                set
                    status = %s,
                    sent_at = %s,
                    provider_message_id = coalesce(%s, provider_message_id),
                    metadata_json = %s::jsonb
                where id = %s
                  and status = any(%s)
                returning {NOTIFICATION_COLUMNS}
                """,
                (
                    to_status.value,
                    sent_at,
                    provider_message_id,
                    json.dumps(metadata_json),
                    notification_id,
                    [status.value for status in from_statuses],
                ),
            )
            record = cursor.fetchone()

        self.connection.commit()
        return NotificationModel.from_record(record) if record else None
