from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg import sql
from psycopg.errors import UndefinedTable

from app.models.task import TaskModel, TaskStatus
from app.schemas.task import CompleteTaskRequest, TaskCreateRequest, TaskFilters, TaskUpdateRequest

logger = logging.getLogger("app.repositories.tasks")

TASK_COLUMNS = """
    id,
    user_id,
    title,
    description,
    priority,
    estimated_minutes,
    actual_minutes,
    energy_required,
    due_at,
    status,
    source,
    metadata_json,
    created_at,
    updated_at,
    completed_at
"""


class TaskRepository:
    def __init__(self, connection: psycopg.Connection) -> None:
        self.connection = connection

    def create_task(self, user_id: str, payload: TaskCreateRequest) -> TaskModel:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                insert into tasks (
                    user_id,
                    title,
                    description,
                    priority,
                    estimated_minutes,
                    energy_required,
                    due_at,
                    status,
                    source,
                    metadata_json
                )
                values (%s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s::jsonb)
                returning {TASK_COLUMNS}
                """,
                (
                    user_id,
                    payload.title,
                    payload.description,
                    payload.priority,
                    payload.estimated_minutes,
                    payload.energy_required,
                    payload.due_at,
                    payload.source,
                    json.dumps(payload.metadata_json),
                ),
            )
            record = cursor.fetchone()

        self.connection.commit()
        return TaskModel.from_record(record)

    def list_tasks(self, user_id: str, filters: TaskFilters) -> list[TaskModel]:
        clauses: list[sql.Composed] = [sql.SQL("user_id = %s")]
        params: list[Any] = [user_id]

        if filters.status is not None:
            clauses.append(sql.SQL("status = %s"))
            params.append(filters.status.value)
        if filters.due_before is not None:
            clauses.append(sql.SQL("due_at <= %s"))
            params.append(filters.due_before)
        if filters.due_after is not None:
            clauses.append(sql.SQL("due_at >= %s"))
            params.append(filters.due_after)
        if filters.priority is not None:
            clauses.append(sql.SQL("priority = %s"))
            params.append(filters.priority)

        query = sql.SQL(
            """
            select {columns}
            from tasks
            where {where_clause}
            order by coalesce(due_at, 'infinity'::timestamptz), created_at desc
            limit %s
            """
        ).format(
            columns=sql.SQL(TASK_COLUMNS),
            where_clause=sql.SQL(" and ").join(clauses),
        )
        params.append(filters.limit)

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            records = cursor.fetchall()

        return [TaskModel.from_record(record) for record in records]

    def list_schedulable_tasks(
        self,
        *,
        user_id: str,
        task_ids: list[str] | None = None,
        limit: int = 100,
    ) -> list[TaskModel]:
        clauses: list[sql.Composed] = [
            sql.SQL("user_id = %s"),
            sql.SQL("status = any(%s)"),
        ]
        params: list[Any] = [
            user_id,
            [
                TaskStatus.PENDING.value,
                TaskStatus.SCHEDULED.value,
                TaskStatus.IN_PROGRESS.value,
            ],
        ]

        if task_ids:
            clauses.append(sql.SQL("id = any(%s)"))
            params.append(task_ids)

        query = sql.SQL(
            """
            select {columns}
            from tasks
            where {where_clause}
            order by coalesce(due_at, 'infinity'::timestamptz), priority desc, created_at asc
            limit %s
            """
        ).format(
            columns=sql.SQL(TASK_COLUMNS),
            where_clause=sql.SQL(" and ").join(clauses),
        )
        params.append(limit)

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            records = cursor.fetchall()

        return [TaskModel.from_record(record) for record in records]

    def list_deadline_watch_candidates(
        self,
        *,
        due_before: datetime,
        user_id: str | None = None,
        limit: int = 200,
    ) -> list[TaskModel]:
        clauses: list[sql.Composed] = [
            sql.SQL("status = any(%s)"),
            sql.SQL("due_at is not null"),
            sql.SQL("due_at <= %s"),
        ]
        params: list[Any] = [
            [
                TaskStatus.PENDING.value,
                TaskStatus.SCHEDULED.value,
                TaskStatus.IN_PROGRESS.value,
            ],
            due_before,
        ]

        if user_id is not None:
            clauses.insert(0, sql.SQL("user_id = %s"))
            params.insert(0, user_id)

        query = sql.SQL(
            """
            select {columns}
            from tasks
            where {where_clause}
            order by due_at asc, priority desc, created_at asc
            limit %s
            """
        ).format(
            columns=sql.SQL(TASK_COLUMNS),
            where_clause=sql.SQL(" and ").join(clauses),
        )
        params.append(limit)

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            records = cursor.fetchall()

        return [TaskModel.from_record(record) for record in records]

    def get_task(self, task_id: str, user_id: str) -> TaskModel | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                select {TASK_COLUMNS}
                from tasks
                where id = %s and user_id = %s
                limit 1
                """,
                (task_id, user_id),
            )
            record = cursor.fetchone()

        return TaskModel.from_record(record) if record else None

    def update_task(self, task_id: str, user_id: str, payload: TaskUpdateRequest) -> TaskModel | None:
        values = {field: getattr(payload, field) for field in payload.model_fields_set}
        return self._update_task_record(task_id=task_id, user_id=user_id, values=values)

    def complete_task(self, task_id: str, user_id: str, payload: CompleteTaskRequest) -> TaskModel | None:
        completed_at = payload.completed_at or datetime.now(timezone.utc)
        values: dict[str, Any] = {
            "status": TaskStatus.DONE.value,
            "completed_at": completed_at,
        }
        if payload.actual_minutes is not None:
            values["actual_minutes"] = payload.actual_minutes
        return self._update_task_record(task_id=task_id, user_id=user_id, values=values)

    def log_task_event(
        self,
        *,
        user_id: str,
        event_type: str,
        task_id: str,
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
                    values (%s, %s, 'task', %s, %s::jsonb)
                    """,
                    (
                        user_id,
                        event_type,
                        task_id,
                        json.dumps(dict(payload or {})),
                    ),
                )
            self.connection.commit()
        except UndefinedTable:
            self.connection.rollback()
            logger.warning("interaction_events table not found; skipped %s event", event_type)

    def _update_task_record(self, *, task_id: str, user_id: str, values: dict[str, Any]) -> TaskModel | None:
        assignments: list[sql.Composed] = []
        params: list[Any] = []

        for column, value in values.items():
            if column == "metadata_json":
                assignments.append(
                    sql.SQL("{} = %s::jsonb").format(sql.Identifier(column))
                )
                params.append(json.dumps(value))
                continue

            if isinstance(value, TaskStatus):
                value = value.value
            assignments.append(sql.SQL("{} = %s").format(sql.Identifier(column)))
            params.append(value)

        assignments.append(sql.SQL("updated_at = now()"))
        params.extend([task_id, user_id])

        query = sql.SQL(
            """
            update tasks
            set {assignments}
            where id = %s and user_id = %s
            returning {columns}
            """
        ).format(
            assignments=sql.SQL(", ").join(assignments),
            columns=sql.SQL(TASK_COLUMNS),
        )

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            record = cursor.fetchone()

        if record is None:
            self.connection.rollback()
            return None

        self.connection.commit()
        return TaskModel.from_record(record)
