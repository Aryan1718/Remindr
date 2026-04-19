from __future__ import annotations

from datetime import timedelta

import psycopg
from psycopg.rows import dict_row

from app.repositories.connectors import ConnectorRepository
from app.repositories.fatigue import FatigueRepository
from app.repositories.internal_calendar import InternalCalendarRepository
from app.repositories.tasks import TaskRepository
from app.repositories.users import UserRepository
from app.services.internal_calendar_service import InternalCalendarService
from app.workers.watchers.deadline_watcher import DeadlineWatcher, DeadlineWatcherResult


def run_deadline_watcher_job(
    *,
    database_url: str,
    user_id: str | None,
    due_within_hours: int,
    limit: int,
) -> list[DeadlineWatcherResult]:
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        scheduling_service = InternalCalendarService(
            connection=connection,
            repository=InternalCalendarRepository(connection),
            task_repository=TaskRepository(connection),
            fatigue_repository=FatigueRepository(connection),
            connector_repository=ConnectorRepository(connection),
            user_repository=UserRepository(connection),
        )
        watcher = DeadlineWatcher(scheduling_service)
        return watcher.run(
            user_id=user_id,
            due_within=timedelta(hours=due_within_hours),
            limit=limit,
        )
