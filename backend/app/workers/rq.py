from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4


_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="fatigue-worker")


@dataclass(slots=True)
class EnqueuedJob:
    job_id: str
    queue_name: str
    status: str
    triggered_at: datetime
    mode: str


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
