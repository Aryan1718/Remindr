from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

import psycopg
from psycopg.errors import UndefinedTable

from app.models.telegram import ConnectorStatus, TelegramConnectorModel

logger = logging.getLogger("app.repositories.telegram")

TELEGRAM_CONNECTOR_COLUMNS = """
    id,
    user_id,
    provider,
    account_email,
    status,
    access_token_encrypted,
    metadata_json,
    last_sync_at,
    created_at,
    updated_at
"""


class TelegramRepository:
    def __init__(self, connection: psycopg.Connection) -> None:
        self.connection = connection

    def get_connector(self, *, user_id: str) -> TelegramConnectorModel | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                select {TELEGRAM_CONNECTOR_COLUMNS}
                from connectors
                where user_id = %s and provider = 'telegram'
                order by updated_at desc
                limit 1
                """,
                (user_id,),
            )
            record = cursor.fetchone()

        return TelegramConnectorModel.from_record(record) if record else None

    def upsert_connector(
        self,
        *,
        user_id: str,
        bot_token: str | None,
        status: ConnectorStatus,
        metadata: dict[str, Any],
        account_email: str | None = "telegram-bot",
    ) -> TelegramConnectorModel:
        existing = self.get_connector(user_id=user_id)

        with self.connection.cursor() as cursor:
            if existing is None:
                cursor.execute(
                    f"""
                    insert into connectors (
                        user_id,
                        provider,
                        account_email,
                        status,
                        access_token_encrypted,
                        metadata_json
                    )
                    values (%s, 'telegram', %s, %s, %s, %s::jsonb)
                    returning {TELEGRAM_CONNECTOR_COLUMNS}
                    """,
                    (
                        user_id,
                        account_email,
                        status.value,
                        bot_token,
                        json.dumps(metadata),
                    ),
                )
            else:
                cursor.execute(
                    f"""
                    update connectors
                    set
                        account_email = %s,
                        status = %s,
                        access_token_encrypted = %s,
                        metadata_json = %s::jsonb,
                        updated_at = now()
                    where id = %s
                    returning {TELEGRAM_CONNECTOR_COLUMNS}
                    """,
                    (
                        account_email,
                        status.value,
                        bot_token,
                        json.dumps(metadata),
                        existing.id,
                    ),
                )
            record = cursor.fetchone()

        self.connection.commit()
        return TelegramConnectorModel.from_record(record)

    def update_connector_metadata(
        self,
        *,
        connector_id: str,
        metadata: dict[str, Any],
        status: ConnectorStatus | None = None,
    ) -> TelegramConnectorModel:
        with self.connection.cursor() as cursor:
            if status is None:
                cursor.execute(
                    f"""
                    update connectors
                    set metadata_json = %s::jsonb, updated_at = now()
                    where id = %s
                    returning {TELEGRAM_CONNECTOR_COLUMNS}
                    """,
                    (json.dumps(metadata), connector_id),
                )
            else:
                cursor.execute(
                    f"""
                    update connectors
                    set metadata_json = %s::jsonb, status = %s, updated_at = now()
                    where id = %s
                    returning {TELEGRAM_CONNECTOR_COLUMNS}
                    """,
                    (json.dumps(metadata), status.value, connector_id),
                )
            record = cursor.fetchone()

        self.connection.commit()
        return TelegramConnectorModel.from_record(record)

    def log_event(
        self,
        *,
        user_id: str,
        event_type: str,
        entity_id: str | None,
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
                    values (%s, %s, 'telegram', %s, %s::jsonb)
                    returning id
                    """,
                    (
                        user_id,
                        event_type,
                        entity_id,
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

    def list_events(self, *, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    select id, event_type, entity_type, entity_id, payload_json, created_at
                    from interaction_events
                    where user_id = %s and entity_type = 'telegram'
                    order by created_at desc
                    limit %s
                    """,
                    (user_id, limit),
                )
                return list(cursor.fetchall())
        except UndefinedTable:
            self.connection.rollback()
            logger.warning("interaction_events table not found; returning no telegram events")
            return []
