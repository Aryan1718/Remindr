from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import datetime
from typing import Any

import psycopg
from psycopg import sql
from psycopg.errors import UndefinedTable

from app.models.fatigue import FatigueCheckinModel, FatiguePatternModel, FatigueTimeBucket
from app.schemas.fatigue import FatigueCheckinCreateRequest, FatiguePatternFilters

logger = logging.getLogger("app.repositories.fatigue")

FATIGUE_CHECKIN_COLUMNS = """
    id,
    user_id,
    score,
    source,
    notes,
    context_json,
    created_at
"""

FATIGUE_PATTERN_COLUMNS = """
    id,
    user_id,
    weekday,
    time_bucket,
    avg_fatigue,
    min_fatigue,
    max_fatigue,
    fatigue_variance,
    sample_count,
    confidence,
    trend_direction,
    last_signal_at,
    last_computed_at,
    metadata_json
"""


class FatigueRepository:
    def __init__(self, connection: psycopg.Connection) -> None:
        self.connection = connection

    def create_checkin(self, *, user_id: str, payload: FatigueCheckinCreateRequest) -> FatigueCheckinModel:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                insert into fatigue_checkins (
                    user_id,
                    score,
                    source,
                    notes,
                    context_json,
                    created_at
                )
                values (%s, %s, %s, %s, %s::jsonb, coalesce(%s, now()))
                returning {FATIGUE_CHECKIN_COLUMNS}
                """,
                (
                    user_id,
                    payload.score,
                    payload.source,
                    payload.notes,
                    json.dumps(payload.context_json),
                    payload.created_at,
                ),
            )
            record = cursor.fetchone()
        self.connection.commit()
        return FatigueCheckinModel.from_record(record)

    def list_checkins(self, *, user_id: str, limit: int = 20) -> list[FatigueCheckinModel]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                select {FATIGUE_CHECKIN_COLUMNS}
                from fatigue_checkins
                where user_id = %s
                order by created_at desc
                limit %s
                """,
                (user_id, limit),
            )
            records = cursor.fetchall()
        return [FatigueCheckinModel.from_record(record) for record in records]

    def get_recent_checkin(self, *, user_id: str, since: datetime) -> FatigueCheckinModel | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                select {FATIGUE_CHECKIN_COLUMNS}
                from fatigue_checkins
                where user_id = %s and created_at >= %s
                order by created_at desc
                limit 1
                """,
                (user_id, since),
            )
            record = cursor.fetchone()
        return FatigueCheckinModel.from_record(record) if record else None

    def list_patterns(self, *, user_id: str, filters: FatiguePatternFilters) -> list[FatiguePatternModel]:
        clauses: list[sql.Composed] = [sql.SQL("user_id = %s")]
        params: list[Any] = [user_id]

        if filters.weekday is not None:
            clauses.append(sql.SQL("weekday = %s"))
            params.append(filters.weekday)
        if filters.time_bucket is not None:
            clauses.append(sql.SQL("time_bucket = %s"))
            params.append(filters.time_bucket.value)

        query = sql.SQL(
            """
            select {columns}
            from fatigue_patterns
            where {where_clause}
            order by weekday asc, time_bucket asc, last_computed_at desc
            limit %s
            """
        ).format(
            columns=sql.SQL(FATIGUE_PATTERN_COLUMNS),
            where_clause=sql.SQL(" and ").join(clauses),
        )
        params.append(filters.limit)

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            records = cursor.fetchall()
        return [FatiguePatternModel.from_record(record) for record in records]

    def get_pattern(
        self,
        *,
        user_id: str,
        weekday: int,
        time_bucket: FatigueTimeBucket,
    ) -> FatiguePatternModel | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                select {FATIGUE_PATTERN_COLUMNS}
                from fatigue_patterns
                where user_id = %s and weekday = %s and time_bucket = %s
                limit 1
                """,
                (user_id, weekday, time_bucket.value),
            )
            record = cursor.fetchone()
        return FatiguePatternModel.from_record(record) if record else None

    def get_user_timezone(self, *, user_id: str) -> str | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                select timezone
                from users
                where id = %s
                limit 1
                """,
                (user_id,),
            )
            record = cursor.fetchone()
        return (record or {}).get("timezone")

    def list_checkins_for_aggregation(
        self,
        *,
        user_id: str | None = None,
        since: datetime | None = None,
    ) -> list[FatigueCheckinModel]:
        clauses: list[sql.Composed] = [sql.SQL("1 = 1")]
        params: list[Any] = []

        if user_id is not None:
            clauses.append(sql.SQL("user_id = %s"))
            params.append(user_id)
        if since is not None:
            clauses.append(sql.SQL("created_at >= %s"))
            params.append(since)

        query = sql.SQL(
            """
            select {columns}
            from fatigue_checkins
            where {where_clause}
            order by created_at desc
            """
        ).format(
            columns=sql.SQL(FATIGUE_CHECKIN_COLUMNS),
            where_clause=sql.SQL(" and ").join(clauses),
        )

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            records = cursor.fetchall()
        return [FatigueCheckinModel.from_record(record) for record in records]

    def upsert_patterns(self, patterns: list[FatiguePatternModel]) -> list[FatiguePatternModel]:
        if not patterns:
            return []

        records: list[dict[str, Any]] = []
        with self.connection.cursor() as cursor:
            for pattern in patterns:
                cursor.execute(
                    f"""
                    insert into fatigue_patterns (
                        user_id,
                        weekday,
                        time_bucket,
                        avg_fatigue,
                        min_fatigue,
                        max_fatigue,
                        fatigue_variance,
                        sample_count,
                        confidence,
                        trend_direction,
                        last_signal_at,
                        last_computed_at,
                        metadata_json
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    on conflict (user_id, weekday, time_bucket)
                    do update set
                        avg_fatigue = excluded.avg_fatigue,
                        min_fatigue = excluded.min_fatigue,
                        max_fatigue = excluded.max_fatigue,
                        fatigue_variance = excluded.fatigue_variance,
                        sample_count = excluded.sample_count,
                        confidence = excluded.confidence,
                        trend_direction = excluded.trend_direction,
                        last_signal_at = excluded.last_signal_at,
                        last_computed_at = excluded.last_computed_at,
                        metadata_json = excluded.metadata_json
                    returning {FATIGUE_PATTERN_COLUMNS}
                    """,
                    (
                        pattern.user_id,
                        pattern.weekday,
                        pattern.time_bucket.value,
                        pattern.avg_fatigue,
                        pattern.min_fatigue,
                        pattern.max_fatigue,
                        pattern.fatigue_variance,
                        pattern.sample_count,
                        pattern.confidence,
                        pattern.trend_direction.value,
                        pattern.last_signal_at,
                        pattern.last_computed_at,
                        json.dumps(pattern.metadata_json),
                    ),
                )
                record = cursor.fetchone()
                if record is not None:
                    records.append(record)
        self.connection.commit()
        return [FatiguePatternModel.from_record(record) for record in records]

    def log_event(
        self,
        *,
        user_id: str,
        event_type: str,
        entity_id: str | None = None,
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
                    values (%s, %s, 'fatigue', %s, %s::jsonb)
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

    def list_patterns_for_distillation(
        self,
        *,
        user_id: str,
        min_confidence: float = 0.0,
        limit: int = 50,
    ) -> list[FatiguePatternModel]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                select {FATIGUE_PATTERN_COLUMNS}
                from fatigue_patterns
                where user_id = %s and confidence >= %s
                order by confidence desc, coalesce(last_computed_at, last_signal_at) desc
                limit %s
                """,
                (user_id, min_confidence, limit),
            )
            records = cursor.fetchall()
        return [FatiguePatternModel.from_record(record) for record in records]
