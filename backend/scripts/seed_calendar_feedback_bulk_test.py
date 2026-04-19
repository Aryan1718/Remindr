from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.db import connect_db, get_database_url
from app.models.internal_calendar import CalendarBlockStatus, CalendarBlockType, FeedbackResponseType
from app.repositories.internal_calendar import InternalCalendarRepository
from app.repositories.memories import MemoryRepository
from app.workers.jobs.memory_distillation import distill_memories_job


@dataclass(slots=True)
class FeedbackSeed:
    starts_at: datetime
    duration_minutes: int
    response_type: FeedbackResponseType
    reason_code: str | None = None
    reason_text: str | None = None
    fatigue_score: int | None = None
    block_type: CalendarBlockType = CalendarBlockType.SUGGESTED_TASK
    title: str = "Focus - Bulk seeded block"


def build_bulk_scenario(*, now: datetime, row_count: int) -> list[FeedbackSeed]:
    templates = [
        {
            "hour": 19,
            "duration": 60,
            "response_type": FeedbackResponseType.REJECTED,
            "reason_code": "too_tired",
            "fatigue_score": 4,
            "block_type": CalendarBlockType.SUGGESTED_TASK,
            "title": "Focus - Evening writing",
        },
        {
            "hour": 20,
            "duration": 60,
            "response_type": FeedbackResponseType.MOVED,
            "reason_code": "busy_at_that_time",
            "fatigue_score": 4,
            "block_type": CalendarBlockType.SUGGESTED_TASK,
            "title": "Focus - Evening planning",
        },
        {
            "hour": 8,
            "duration": 45,
            "response_type": FeedbackResponseType.ACCEPTED,
            "reason_code": None,
            "fatigue_score": 1,
            "block_type": CalendarBlockType.FOCUS_BLOCK,
            "title": "Focus - Morning review",
        },
        {
            "hour": 9,
            "duration": 45,
            "response_type": FeedbackResponseType.COMPLETED,
            "reason_code": None,
            "fatigue_score": 1,
            "block_type": CalendarBlockType.FOCUS_BLOCK,
            "title": "Focus - Morning execution",
        },
        {
            "hour": 21,
            "duration": 30,
            "response_type": FeedbackResponseType.ACCEPTED,
            "reason_code": None,
            "fatigue_score": 2,
            "block_type": CalendarBlockType.SUGGESTED_TASK,
            "title": "Focus - Night inbox cleanup",
        },
        {
            "hour": 21,
            "duration": 90,
            "response_type": FeedbackResponseType.REJECTED,
            "reason_code": "too_long",
            "fatigue_score": 4,
            "block_type": CalendarBlockType.SUGGESTED_TASK,
            "title": "Focus - Night deep work",
        },
    ]

    seeds: list[FeedbackSeed] = []
    base_day = now.replace(minute=0, second=0, microsecond=0) - timedelta(days=row_count)
    for index in range(row_count):
        template = templates[index % len(templates)]
        starts_at = (base_day + timedelta(days=index)).replace(hour=template["hour"])
        if index % 6 == 3:
            starts_at = starts_at + timedelta(minutes=30)
        seeds.append(
            FeedbackSeed(
                starts_at=starts_at,
                duration_minutes=int(template["duration"]),
                response_type=template["response_type"],
                reason_code=template["reason_code"],
                reason_text=f"bulk-seeded row {index + 1}",
                fatigue_score=template["fatigue_score"],
                block_type=template["block_type"],
                title=f"{template['title']} #{index + 1}",
            )
        )
    return seeds


def seed_feedback(*, connection: psycopg.Connection, user_id: str, seeds: list[FeedbackSeed]) -> list[str]:
    repository = InternalCalendarRepository(connection)
    feedback_ids: list[str] = []

    for index, seed in enumerate(seeds, start=1):
        block = repository.create_block(
            user_id=user_id,
            task_id=None,
            title=seed.title,
            block_type=seed.block_type,
            starts_at=seed.starts_at,
            ends_at=seed.starts_at + timedelta(minutes=seed.duration_minutes),
            status=CalendarBlockStatus.SUGGESTED,
            sync_to_google=False,
            source="bulk_seed_script",
            reason_summary="Bulk-seeded calendar feedback test block",
            priority_snapshot=3,
            energy_snapshot=2,
            metadata_json={"seed_script": True, "seed_index": index, "bulk_seed": True},
        )
        feedback = repository.insert_feedback(
            block_id=block.id,
            user_id=user_id,
            response_type=seed.response_type,
            reason_code=seed.reason_code,
            reason_text=seed.reason_text,
            fatigue_score=seed.fatigue_score,
        )
        feedback_ids.append(feedback.id)

    return feedback_ids


def print_recent_memories(*, connection: psycopg.Connection, user_id: str) -> None:
    repository = MemoryRepository(connection)
    memories = repository.list_recent_memories(user_id=user_id, limit=15)
    print("\nRecent learned memories:")
    if not memories:
        print("  none")
        return
    for memory in memories:
        print(f"  - {memory.statement} | confidence={memory.confidence} | metadata={memory.metadata_json}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed 50 raw calendar_feedback rows and invoke memory distillation for testing."
    )
    parser.add_argument("--user-id", required=True, help="Target user id")
    parser.add_argument(
        "--row-count",
        default=50,
        type=int,
        help="Number of raw calendar_feedback rows to insert",
    )
    parser.add_argument(
        "--skip-distill",
        action="store_true",
        help="Only insert raw rows and skip invoking the distillation job",
    )
    args = parser.parse_args()

    now = datetime.now(UTC)
    seeds = build_bulk_scenario(now=now, row_count=args.row_count)

    database_url = get_database_url()
    with connect_db(database_url=database_url) as connection:
        feedback_ids = seed_feedback(connection=connection, user_id=args.user_id, seeds=seeds)
        print(f"Inserted {len(feedback_ids)} raw calendar_feedback rows for user {args.user_id}.")
        print(f"First 10 feedback ids: {', '.join(feedback_ids[:10])}")

        if not args.skip_distill:
            result = distill_memories_job(
                connection=connection,
                user_id=args.user_id,
                days_back=90,
                trigger_source="seed_calendar_feedback_bulk_test",
                entity_type="calendar_feedback",
            )
            print(f"Distillation result: {result}")

        print_recent_memories(connection=connection, user_id=args.user_id)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
