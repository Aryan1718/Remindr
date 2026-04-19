from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any

import psycopg
from psycopg import sql
from psycopg.errors import UndefinedTable

from app.models.connector import ConnectorModel, ConnectorProvider, ConnectorStatus
from app.models.external_calendar_event import ExternalCalendarEventModel

logger = logging.getLogger("app.repositories.connectors")

CONNECTOR_COLUMNS = """
    id,
    user_id,
    provider,
    account_email,
    status,
    access_token_encrypted,
    refresh_token_encrypted,
    token_expires_at,
    last_sync_at,
    metadata_json,
    created_at,
    updated_at
"""

EXTERNAL_CALENDAR_EVENT_COLUMNS = """
    id,
    user_id,
    connector_id,
    external_event_id,
    calendar_id,
    title,
    description,
    location,
    starts_at,
    ends_at,
    is_all_day,
    status,
    raw_payload_json,
    last_synced_at,
    created_at,
    updated_at
"""


class ConnectorRepository:
    def __init__(self, connection: psycopg.Connection) -> None:
        self.connection = connection

    def list_connectors(self, *, user_id: str) -> list[ConnectorModel]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                select {CONNECTOR_COLUMNS}
                from connectors
                where user_id = %s
                order by provider asc, updated_at desc
                """,
                (user_id,),
            )
            records = cursor.fetchall()
        return [ConnectorModel.from_record(record) for record in records]

    def get_connector(
        self,
        *,
        connector_id: str,
        user_id: str,
    ) -> ConnectorModel | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                select {CONNECTOR_COLUMNS}
                from connectors
                where id = %s and user_id = %s
                limit 1
                """,
                (connector_id, user_id),
            )
            record = cursor.fetchone()
        return ConnectorModel.from_record(record) if record else None

    def get_connector_by_provider(
        self,
        *,
        user_id: str,
        provider: ConnectorProvider,
        account_email: str | None = None,
    ) -> ConnectorModel | None:
        clauses = ["user_id = %s", "provider = %s"]
        params: list[Any] = [user_id, provider.value]
        if account_email is not None:
            clauses.append("account_email = %s")
            params.append(account_email)

        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                select {CONNECTOR_COLUMNS}
                from connectors
                where {" and ".join(clauses)}
                order by updated_at desc
                limit 1
                """,
                params,
            )
            record = cursor.fetchone()
        return ConnectorModel.from_record(record) if record else None

    def upsert_connector(
        self,
        *,
        user_id: str,
        provider: ConnectorProvider,
        account_email: str | None,
        access_token: str | None,
        refresh_token: str | None,
        token_expires_at: datetime | None,
        metadata: dict[str, Any],
        status: ConnectorStatus,
    ) -> ConnectorModel:
        existing = self.get_connector_by_provider(
            user_id=user_id,
            provider=provider,
            account_email=account_email,
        )

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
                        refresh_token_encrypted,
                        token_expires_at,
                        metadata_json
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    returning {CONNECTOR_COLUMNS}
                    """,
                    (
                        user_id,
                        provider.value,
                        account_email,
                        status.value,
                        access_token,
                        refresh_token,
                        token_expires_at,
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
                        refresh_token_encrypted = %s,
                        token_expires_at = %s,
                        metadata_json = %s::jsonb,
                        updated_at = now()
                    where id = %s and user_id = %s
                    returning {CONNECTOR_COLUMNS}
                    """,
                    (
                        account_email,
                        status.value,
                        access_token,
                        refresh_token,
                        token_expires_at,
                        json.dumps(metadata),
                        existing.id,
                        user_id,
                    ),
                )
            record = cursor.fetchone()

        self.connection.commit()
        return ConnectorModel.from_record(record)

    def update_connector_sync_state(
        self,
        *,
        connector_id: str,
        user_id: str,
        status: ConnectorStatus,
        metadata: dict[str, Any],
        last_sync_at: datetime | None,
    ) -> ConnectorModel | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                update connectors
                set
                    status = %s,
                    metadata_json = %s::jsonb,
                    last_sync_at = %s,
                    updated_at = now()
                where id = %s and user_id = %s
                returning {CONNECTOR_COLUMNS}
                """,
                (
                    status.value,
                    json.dumps(metadata),
                    last_sync_at,
                    connector_id,
                    user_id,
                ),
            )
            record = cursor.fetchone()

        if record is None:
            self.connection.rollback()
            return None

        self.connection.commit()
        return ConnectorModel.from_record(record)

    def upsert_external_calendar_events(self, events: Iterable[Mapping[str, Any]]) -> int:
        deduped: dict[tuple[str, str], Mapping[str, Any]] = {}
        for event in events:
            key = (str(event["connector_id"]), str(event["external_event_id"]))
            deduped[key] = event

        rows = [
            (
                event["user_id"],
                event["connector_id"],
                event["external_event_id"],
                event.get("calendar_id"),
                event.get("title"),
                event.get("description"),
                event.get("location"),
                event["starts_at"],
                event["ends_at"],
                event["is_all_day"],
                event.get("status"),
                json.dumps(event.get("raw_payload_json") or {}),
                event.get("last_synced_at"),
            )
            for event in deduped.values()
        ]
        if not rows:
            return 0

        with self.connection.cursor() as cursor:
            cursor.executemany(
                """
                insert into external_calendar_events (
                    user_id,
                    connector_id,
                    external_event_id,
                    calendar_id,
                    title,
                    description,
                    location,
                    starts_at,
                    ends_at,
                    is_all_day,
                    status,
                    raw_payload_json,
                    last_synced_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                on conflict (connector_id, external_event_id)
                do update set
                    calendar_id = excluded.calendar_id,
                    title = excluded.title,
                    description = excluded.description,
                    location = excluded.location,
                    starts_at = excluded.starts_at,
                    ends_at = excluded.ends_at,
                    is_all_day = excluded.is_all_day,
                    status = excluded.status,
                    raw_payload_json = excluded.raw_payload_json,
                    last_synced_at = excluded.last_synced_at,
                    updated_at = now()
                """,
                rows,
            )
        self.connection.commit()
        return len(rows)

    def list_external_calendar_events(
        self,
        *,
        user_id: str,
        start: datetime,
        end: datetime,
        limit: int = 200,
    ) -> list[ExternalCalendarEventModel]:
        query = sql.SQL(
            """
            select {columns}
            from external_calendar_events
            where user_id = %s
              and starts_at < %s
              and ends_at > %s
            order by starts_at asc
            limit %s
            """
        ).format(columns=sql.SQL(EXTERNAL_CALENDAR_EVENT_COLUMNS))
        with self.connection.cursor() as cursor:
            cursor.execute(query, (user_id, end, start, limit))
            records = cursor.fetchall()
        return [ExternalCalendarEventModel.from_record(record) for record in records]

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
                    values (%s, %s, 'connector', %s, %s::jsonb)
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
