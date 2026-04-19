from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from app.core.config import get_settings
from app.workers.constants import (
    CONNECTOR_SYNC_JOB_TYPE,
    CONNECTOR_SYNC_QUEUE,
    MEMORY_DISTILLATION_JOB,
    MEMORY_DISTILLATION_QUEUE,
    NOTIFICATION_DELIVERY_JOB,
    NOTIFICATION_DELIVERY_QUEUE,
)


_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="fatigue-worker")


@dataclass(slots=True)
class EnqueuedJob:
    job_id: str
    queue_name: str
    status: str
    triggered_at: datetime
    mode: str

    @property
    def job_type(self) -> str:
        return self.queue_name

    @property
    def job_status(self) -> str:
        return self.status


def enqueue_callable(*, queue_name: str, fn, mode: str = "async", **kwargs) -> EnqueuedJob:
    triggered_at = datetime.now(UTC)
    job_id = str(uuid4())

    if mode == "inline":
        fn(**kwargs)
        return EnqueuedJob(
            job_id=job_id,
            queue_name=queue_name,
            status="completed",
            triggered_at=triggered_at,
            mode="inline",
        )

    _executor.submit(fn, **kwargs)
    return EnqueuedJob(
        job_id=job_id,
        queue_name=queue_name,
        status="queued",
        triggered_at=triggered_at,
        mode="async",
    )


def enqueue_connector_sync(
    *,
    connector_id: str,
    user_id: str,
    lookahead_days: int,
    lookback_days: int,
    force: bool,
) -> EnqueuedJob:
    from app.workers.jobs.connector_sync import sync_connector_job

    mode = "inline" if get_settings().connector_sync_eager else "async"
    job = enqueue_callable(
        queue_name=CONNECTOR_SYNC_QUEUE,
        fn=sync_connector_job,
        mode=mode,
        connector_id=connector_id,
        user_id=user_id,
        lookahead_days=lookahead_days,
        lookback_days=lookback_days,
        force=force,
    )
    return EnqueuedJob(
        job_id=job.job_id,
        queue_name=CONNECTOR_SYNC_JOB_TYPE,
        status=job.status,
        triggered_at=job.triggered_at,
        mode=job.mode,
    )


def enqueue_memory_distillation(
    *,
    user_id: str | None,
    days_back: int = 45,
    trigger_source: str | None = None,
    force: bool = False,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> EnqueuedJob:
    from app.workers.jobs.memory_distillation import distill_memories_job

    settings = get_settings()
    mode = "inline" if settings.memory_distillation_eager else "async"
    job = enqueue_callable(
        queue_name=MEMORY_DISTILLATION_QUEUE,
        fn=distill_memories_job,
        mode=mode,
        user_id=user_id,
        days_back=days_back,
        trigger_source=trigger_source,
        force=force,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    return EnqueuedJob(
        job_id=job.job_id,
        queue_name=MEMORY_DISTILLATION_JOB,
        status=job.status,
        triggered_at=job.triggered_at,
        mode=job.mode,
    )


def enqueue_notification_delivery(*, notification_id: str) -> EnqueuedJob:
    from app.workers.jobs.notification_jobs import deliver_notification_job

    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    mode = "inline" if getattr(settings, "notification_delivery_eager", True) else "async"
    job = enqueue_callable(
        queue_name=NOTIFICATION_DELIVERY_QUEUE,
        fn=deliver_notification_job,
        mode=mode,
        database_url=settings.database_url,
        notification_id=notification_id,
    )
    return EnqueuedJob(
        job_id=job.job_id,
        queue_name=NOTIFICATION_DELIVERY_JOB,
        status=job.status,
        triggered_at=job.triggered_at,
        mode=job.mode,
    )
