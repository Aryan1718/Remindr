from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
from psycopg.errors import UndefinedTable
from psycopg.rows import dict_row

from app.core.db import get_database_url
from app.services.memory_service import MemoryService


def distill_memories_job(
    *,
    database_url: str | None = None,
    user_id: str | None = None,
    days_back: int = 45,
    trigger_source: str | None = None,
    force: bool = False,
    entity_type: str | None = None,
    entity_id: str | None = None,
    connection: psycopg.Connection | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    effective_now = as_of or datetime.now(UTC)
    owns_connection = connection is None
    connection = connection or psycopg.connect(database_url or get_database_url(), row_factory=dict_row)
    service = MemoryService(connection)

    try:
        target_user_ids = [user_id] if user_id is not None else _list_candidate_user_ids(connection=connection, since=effective_now - timedelta(days=days_back))
        persisted_count = 0
        user_results: dict[str, int] = {}

        for target_user_id in target_user_ids:
            stored = service.distill_memories_for_user(user_id=target_user_id, days_back=days_back, as_of=effective_now)
            user_results[target_user_id] = len(stored)
            persisted_count += len(stored)
            _log_memory_event(
                connection=connection,
                user_id=target_user_id,
                payload={
                    "memory_count": len(stored),
                    "days_back": days_back,
                    **({"trigger_source": trigger_source} if trigger_source is not None else {}),
                    **({"force": force} if force else {}),
                    **({"entity_type": entity_type} if entity_type is not None else {}),
                    **({"entity_id": entity_id} if entity_id is not None else {}),
                },
            )

        return {
            "user_count": len(target_user_ids),
            "memory_count": persisted_count,
            "target_user_ids": target_user_ids,
            "user_results": user_results,
        }
    finally:
        if owns_connection:
            connection.close()


def _list_candidate_user_ids(*, connection: psycopg.Connection, since: datetime) -> list[str]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select distinct user_id::text as user_id
            from (
                select user_id from interaction_events where created_at >= %s
                union
                select user_id from calendar_feedback where created_at >= %s
                union
                select user_id from fatigue_checkins where created_at >= %s
                union
                select user_id from fatigue_patterns where coalesce(last_computed_at, last_signal_at) >= %s
            ) signal_users
            order by user_id asc
            """,
            (since, since, since, since),
        )
        records = cursor.fetchall()
    return [str(record["user_id"]) for record in records]


def _log_memory_event(*, connection: psycopg.Connection, user_id: str, payload: dict[str, Any]) -> None:
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into interaction_events (
                    user_id,
                    event_type,
                    entity_type,
                    payload_json
                )
                values (%s, 'memory_distilled', 'memory', %s::jsonb)
                """,
                (user_id, json.dumps(payload)),
            )
        connection.commit()
    except UndefinedTable:
        connection.rollback()
