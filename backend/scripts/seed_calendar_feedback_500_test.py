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
    title: str = "Focus - 500 row seeded block"


def build_seeds(*, now: datetime, row_count: int) -> list[FeedbackSeed]:
    seeds: list[FeedbackSeed] = []
    base_day = now.replace(minute=0, second=0, microsecond=0) - timedelta(days=row_count // 2)

    for index in range(row_count):
        day = base_day + timedelta(days=index // 2)
        slot = index % 10

        if slot in {0, 1, 2}:
            starts_at = day.replace(hour=19 + (slot % 2), minute=0)
            seeds.append(
                FeedbackSeed(
                    starts_at=starts_at,
                    duration_minutes=60,
                    response_type=FeedbackResponseType.REJECTED if slot != 1 else FeedbackResponseType.MOVED,
                    reason_code="too_tired" if slot != 1 else "busy_at_that_time",
                    reason_text=f"seeded evening resistance #{index + 1}",
                    fatigue_score=4,
                    block_type=CalendarBlockType.SUGGESTED_TASK,
                    title=f"Focus - Evening deep work #{index + 1}",
                )
            )
            continue

        if slot in {3, 4, 5}:
            starts_at = day.replace(hour=8 + (slot - 3), minute=0)
            seeds.append(
                FeedbackSeed(
                    starts_at=starts_at,
                    duration_minutes=45,
                    response_type=FeedbackResponseType.ACCEPTED if slot != 5 else FeedbackResponseType.COMPLETED,
                    reason_text=f"seeded morning acceptance #{index + 1}",
                    fatigue_score=1,
                    block_type=CalendarBlockType.FOCUS_BLOCK,
                    title=f"Focus - Morning execution #{index + 1}",
                )
            )
            continue

        if slot in {6, 7}:
            starts_at = day.replace(hour=21, minute=30 if slot == 7 else 0)
            seeds.append(
                FeedbackSeed(
                    starts_at=starts_at,
                    duration_minutes=30,
                    response_type=FeedbackResponseType.ACCEPTED if slot == 6 else FeedbackResponseType.COMPLETED,
                    reason_text=f"seeded short night block #{index + 1}",
                    fatigue_score=2,
                    block_type=CalendarBlockType.SUGGESTED_TASK,
                    title=f"Focus - Short night block #{index + 1}",
                )
            )
            continue

        starts_at = day.replace(hour=21 if slot == 8 else 20, minute=0)
        seeds.append(
            FeedbackSeed(
                starts_at=starts_at,
                duration_minutes=90,
                response_type=FeedbackResponseType.REJECTED if slot == 8 else FeedbackResponseType.MOVED,
                reason_code="too_long" if slot == 8 else "busy_at_that_time",
                reason_text=f"seeded long late block #{index + 1}",
                fatigue_score=4,
                block_type=CalendarBlockType.SUGGESTED_TASK,
                title=f"Focus - Long late block #{index + 1}",
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
            source="seed_500_script",
            reason_summary="500-row seeded calendar feedback test block",
            priority_snapshot=3,
            energy_snapshot=2,
            metadata_json={"seed_script": True, "seed_index": index, "bulk_size": 500},
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
    memories = repository.list_recent_memories(user_id=user_id, limit=20)
    print("\nRecent learned memories:")
    if not memories:
        print("  none")
        return
    for memory in memories:
        print(f"  - {memory.statement} | confidence={memory.confidence} | metadata={memory.metadata_json}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed 500 raw calendar_feedback rows and invoke memory distillation."
    )
    parser.add_argument("--user-id", required=True, help="Target user id")
    parser.add_argument(
        "--row-count",
        default=500,
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
    seeds = build_seeds(now=now, row_count=args.row_count)
    database_url = get_database_url()

    with connect_db(database_url=database_url) as connection:
        feedback_ids = seed_feedback(connection=connection, user_id=args.user_id, seeds=seeds)
        print(f"Inserted {len(feedback_ids)} raw calendar_feedback rows for user {args.user_id}.")
        print(f"First 10 feedback ids: {', '.join(feedback_ids[:10])}")

        if not args.skip_distill:
            result = distill_memories_job(
                connection=connection,
                user_id=args.user_id,
                days_back=365,
                trigger_source="seed_calendar_feedback_500_test",
                entity_type="calendar_feedback",
            )
            print(f"Distillation result: {result}")

        print_recent_memories(connection=connection, user_id=args.user_id)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
