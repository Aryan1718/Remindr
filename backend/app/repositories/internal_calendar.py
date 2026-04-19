from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import datetime
from typing import Any

import psycopg
from psycopg import sql
from psycopg.errors import UndefinedTable

from app.models.internal_calendar import (
    CalendarBlockStatus,
    CalendarBlockType,
    CalendarFeedbackModel,
    FeedbackResponseType,
    InternalCalendarBlockModel,
)

logger = logging.getLogger("app.repositories.internal_calendar")

INTERNAL_CALENDAR_COLUMNS = """
    id,
    user_id,
    task_id,
    title,
    block_type,
    starts_at,
    ends_at,
    status,
    sync_to_google,
    external_event_id,
    source,
    reason_summary,
    reschedule_count,
    priority_snapshot,
    energy_snapshot,
    metadata_json,
    created_at,
    updated_at,
    confirmed_at,
    rejected_at,
    completed_at
"""

CALENDAR_FEEDBACK_COLUMNS = """
    id,
    calendar_block_id,
    user_id,
    response_type,
    reason_code,
    reason_text,
    fatigue_score,
    created_at
"""


class InternalCalendarRepository:
    def __init__(self, connection: psycopg.Connection) -> None:
        self.connection = connection

    def create_block(
        self,
        *,
        user_id: str,
        task_id: str | None,
        title: str,
        block_type: CalendarBlockType,
        starts_at: datetime,
        ends_at: datetime,
        status: CalendarBlockStatus,
        sync_to_google: bool,
        source: str,
        reason_summary: str | None,
        priority_snapshot: int | None,
        energy_snapshot: int | None,
        metadata_json: dict[str, Any] | None = None,
    ) -> InternalCalendarBlockModel:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                insert into internal_calendar (
                    user_id,
                    task_id,
                    title,
                    block_type,
                    starts_at,
                    ends_at,
                    status,
                    sync_to_google,
                    source,
                    reason_summary,
                    priority_snapshot,
                    energy_snapshot,
                    metadata_json
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                returning {INTERNAL_CALENDAR_COLUMNS}
                """,
                (
                    user_id,
                    task_id,
                    title,
                    block_type.value,
                    starts_at,
                    ends_at,
                    status.value,
                    sync_to_google,
                    source,
                    reason_summary,
                    priority_snapshot,
                    energy_snapshot,
                    json.dumps(metadata_json or {}),
                ),
            )
            record = cursor.fetchone()

        self.connection.commit()
        return InternalCalendarBlockModel.from_record(record)

    def list_blocks(
        self,
        *,
        user_id: str,
        start: datetime | None = None,
        end: datetime | None = None,
        status: CalendarBlockStatus | None = None,
        task_id: str | None = None,
        limit: int = 100,
    ) -> list[InternalCalendarBlockModel]:
        clauses: list[sql.Composed] = [sql.SQL("user_id = %s")]
        params: list[Any] = [user_id]

        if start is not None:
            clauses.append(sql.SQL("ends_at >= %s"))
            params.append(start)
        if end is not None:
            clauses.append(sql.SQL("starts_at <= %s"))
            params.append(end)
        if status is not None:
            clauses.append(sql.SQL("status = %s"))
            params.append(status.value)
        if task_id is not None:
            clauses.append(sql.SQL("task_id = %s"))
            params.append(task_id)

        query = sql.SQL(
            """
            select {columns}
            from internal_calendar
            where {where_clause}
            order by starts_at asc, created_at asc
            limit %s
            """
        ).format(
            columns=sql.SQL(INTERNAL_CALENDAR_COLUMNS),
            where_clause=sql.SQL(" and ").join(clauses),
        )
        params.append(limit)

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            records = cursor.fetchall()

        return [InternalCalendarBlockModel.from_record(record) for record in records]

    def list_future_blocks(
        self,
        *,
        user_id: str,
        starts_after: datetime,
        ends_before: datetime | None = None,
        limit: int = 200,
    ) -> list[InternalCalendarBlockModel]:
        return self.list_blocks(
            user_id=user_id,
            start=starts_after,
            end=ends_before,
            limit=limit,
        )

    def get_block(self, *, block_id: str, user_id: str) -> InternalCalendarBlockModel | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                select {INTERNAL_CALENDAR_COLUMNS}
                from internal_calendar
                where id = %s and user_id = %s
                limit 1
                """,
                (block_id, user_id),
            )
            record = cursor.fetchone()

        return InternalCalendarBlockModel.from_record(record) if record else None

    def list_feedback_for_block(self, *, block_id: str, user_id: str) -> list[CalendarFeedbackModel]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                select {CALENDAR_FEEDBACK_COLUMNS}
                from calendar_feedback
                where calendar_block_id = %s and user_id = %s
                order by created_at desc
                """,
                (block_id, user_id),
            )
            records = cursor.fetchall()

        return [CalendarFeedbackModel.from_record(record) for record in records]

    def list_blocks_in_window(
        self,
        *,
        user_id: str,
        window_start: datetime,
        window_end: datetime,
        exclude_block_id: str | None = None,
    ) -> list[InternalCalendarBlockModel]:
        clauses: list[sql.Composed] = [
            sql.SQL("user_id = %s"),
            sql.SQL("starts_at < %s"),
            sql.SQL("ends_at > %s"),
        ]
        params: list[Any] = [user_id, window_end, window_start]

        if exclude_block_id is not None:
            clauses.append(sql.SQL("id <> %s"))
            params.append(exclude_block_id)

        query = sql.SQL(
            """
            select {columns}
            from internal_calendar
            where {where_clause}
            order by starts_at asc, created_at asc
            """
        ).format(
            columns=sql.SQL(INTERNAL_CALENDAR_COLUMNS),
            where_clause=sql.SQL(" and ").join(clauses),
        )

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            records = cursor.fetchall()

        return [InternalCalendarBlockModel.from_record(record) for record in records]

    def list_task_blocks_in_window(
        self,
        *,
        user_id: str,
        task_id: str,
        window_start: datetime,
        window_end: datetime,
    ) -> list[InternalCalendarBlockModel]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                select {INTERNAL_CALENDAR_COLUMNS}
                from internal_calendar
                where user_id = %s
                  and task_id = %s
                  and starts_at < %s
                  and ends_at > %s
                order by starts_at asc, created_at asc
                """,
                (user_id, task_id, window_end, window_start),
            )
            records = cursor.fetchall()

        return [InternalCalendarBlockModel.from_record(record) for record in records]

    def update_block(
        self,
        *,
        block_id: str,
        user_id: str,
        values: dict[str, Any],
    ) -> InternalCalendarBlockModel | None:
        assignments: list[sql.Composed] = []
        params: list[Any] = []

        for column, value in values.items():
            if column == "metadata_json":
                assignments.append(sql.SQL("{} = %s::jsonb").format(sql.Identifier(column)))
                params.append(json.dumps(value))
                continue
            if isinstance(value, (CalendarBlockStatus, CalendarBlockType)):
                value = value.value
            assignments.append(sql.SQL("{} = %s").format(sql.Identifier(column)))
            params.append(value)

        assignments.append(sql.SQL("updated_at = now()"))
        params.extend([block_id, user_id])

        query = sql.SQL(
            """
            update internal_calendar
            set {assignments}
            where id = %s and user_id = %s
            returning {columns}
            """
        ).format(
            assignments=sql.SQL(", ").join(assignments),
            columns=sql.SQL(INTERNAL_CALENDAR_COLUMNS),
        )

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            record = cursor.fetchone()

        if record is None:
            self.connection.rollback()
            return None

        self.connection.commit()
        return InternalCalendarBlockModel.from_record(record)

    def insert_feedback(
        self,
        *,
        block_id: str,
        user_id: str,
        response_type: FeedbackResponseType,
        reason_code: str | None = None,
        reason_text: str | None = None,
        fatigue_score: int | None = None,
    ) -> CalendarFeedbackModel:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                insert into calendar_feedback (
                    calendar_block_id,
                    user_id,
                    response_type,
                    reason_code,
                    reason_text,
                    fatigue_score
                )
                values (%s, %s, %s, %s, %s, %s)
                returning {CALENDAR_FEEDBACK_COLUMNS}
                """,
                (
                    block_id,
                    user_id,
                    response_type.value,
                    reason_code,
                    reason_text,
                    fatigue_score,
                ),
            )
            record = cursor.fetchone()

        self.connection.commit()
        return CalendarFeedbackModel.from_record(record)

    def log_calendar_event(
        self,
        *,
        user_id: str,
        event_type: str,
        block_id: str,
        payload: Mapping[str, Any] | None = None,
    ) -> None:
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
                    values (%s, %s, 'internal_calendar', %s, %s::jsonb)
                    """,
                    (
                        user_id,
                        event_type,
                        block_id,
                        json.dumps(dict(payload or {})),
                    ),
                )
            self.connection.commit()
        except UndefinedTable:
            self.connection.rollback()
            logger.warning("interaction_events table not found; skipped %s event", event_type)
