from __future__ import annotations

from app.core.config import get_settings
from app.workers.constants import FATIGUE_QUEUE_NAME, WATCHER_QUEUE_NAME
from app.workers.jobs.fatigue_aggregation import recompute_fatigue_patterns_job
from app.workers.jobs.watcher_jobs import run_deadline_watcher_job
from app.workers.rq import EnqueuedJob, enqueue_callable


def enqueue_fatigue_pattern_recompute(*, user_id: str, days_back: int, mode: str = "async") -> EnqueuedJob:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    return enqueue_callable(
        queue_name=FATIGUE_QUEUE_NAME,
        fn=recompute_fatigue_patterns_job,
        mode=mode,
        database_url=settings.database_url,
        user_id=user_id,
        days_back=days_back,
    )


def enqueue_deadline_watcher(
    *,
    user_id: str | None = None,
    due_within_hours: int = 72,
    limit: int = 200,
    mode: str = "async",
) -> EnqueuedJob:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    return enqueue_callable(
        queue_name=WATCHER_QUEUE_NAME,
        fn=run_deadline_watcher_job,
        mode=mode,
        database_url=settings.database_url,
        user_id=user_id,
        due_within_hours=due_within_hours,
        limit=limit,
    )
