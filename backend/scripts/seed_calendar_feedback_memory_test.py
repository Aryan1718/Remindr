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
    title: str = "Focus - Seeded block"


def build_scenario(name: str, now: datetime) -> list[FeedbackSeed]:
    if name == "evening_rejections":
        return [
            FeedbackSeed(
                starts_at=now.replace(hour=19, minute=0, second=0, microsecond=0) - timedelta(days=2),
                duration_minutes=60,
                response_type=FeedbackResponseType.REJECTED,
                reason_code="too_tired",
                fatigue_score=4,
                title="Focus - Writing",
            ),
            FeedbackSeed(
                starts_at=now.replace(hour=20, minute=0, second=0, microsecond=0) - timedelta(days=1),
                duration_minutes=60,
                response_type=FeedbackResponseType.MOVED,
                reason_code="busy_at_that_time",
                fatigue_score=4,
                title="Focus - Planning",
            ),
            FeedbackSeed(
                starts_at=now.replace(hour=8, minute=0, second=0, microsecond=0),
                duration_minutes=45,
                response_type=FeedbackResponseType.ACCEPTED,
                fatigue_score=1,
                block_type=CalendarBlockType.FOCUS_BLOCK,
                title="Focus - Morning review",
            ),
            FeedbackSeed(
                starts_at=now.replace(hour=8, minute=30, second=0, microsecond=0) + timedelta(days=1),
                duration_minutes=45,
                response_type=FeedbackResponseType.COMPLETED,
                fatigue_score=1,
                block_type=CalendarBlockType.FOCUS_BLOCK,
                title="Focus - Morning execution",
            ),
        ]
    if name == "night_short_blocks":
        return [
            FeedbackSeed(
                starts_at=now.replace(hour=21, minute=0, second=0, microsecond=0) - timedelta(days=2),
                duration_minutes=30,
                response_type=FeedbackResponseType.ACCEPTED,
                fatigue_score=2,
                title="Focus - Inbox cleanup",
            ),
            FeedbackSeed(
                starts_at=now.replace(hour=21, minute=30, second=0, microsecond=0) - timedelta(days=1),
                duration_minutes=90,
                response_type=FeedbackResponseType.REJECTED,
                reason_code="too_long",
                fatigue_score=4,
                title="Focus - Deep work",
            ),
            FeedbackSeed(
                starts_at=now.replace(hour=22, minute=0, second=0, microsecond=0),
                duration_minutes=30,
                response_type=FeedbackResponseType.COMPLETED,
                fatigue_score=2,
                title="Focus - Small task sprint",
            ),
        ]
    raise ValueError(f"Unsupported scenario: {name}")


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
            source="seed_script",
            reason_summary="Seeded calendar feedback test block",
            priority_snapshot=3,
            energy_snapshot=2,
            metadata_json={"seed_script": True, "seed_index": index},
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
    memories = repository.list_recent_memories(user_id=user_id, limit=10)
    print("\nRecent learned memories:")
    if not memories:
        print("  none")
        return
    for memory in memories:
        print(f"  - {memory.statement} | confidence={memory.confidence} | metadata={memory.metadata_json}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed raw calendar_feedback rows and invoke memory distillation for testing."
    )
    parser.add_argument("--user-id", required=True, help="Target user id")
    parser.add_argument(
        "--scenario",
        default="evening_rejections",
        choices=["evening_rejections", "night_short_blocks"],
        help="Seed scenario to insert",
    )
    parser.add_argument(
        "--skip-distill",
        action="store_true",
        help="Only insert raw rows and skip invoking the distillation job",
    )
    args = parser.parse_args()

    now = datetime.now(UTC)
    seeds = build_scenario(args.scenario, now)

    database_url = get_database_url()
    with connect_db(database_url=database_url) as connection:
        feedback_ids = seed_feedback(connection=connection, user_id=args.user_id, seeds=seeds)
        print(f"Inserted {len(feedback_ids)} raw calendar_feedback rows for user {args.user_id}.")
        print(f"Feedback ids: {', '.join(feedback_ids)}")

        if not args.skip_distill:
            result = distill_memories_job(
                connection=connection,
                user_id=args.user_id,
                days_back=45,
                trigger_source="seed_calendar_feedback_memory_test",
                entity_type="calendar_feedback",
            )
            print(f"Distillation result: {result}")

        print_recent_memories(connection=connection, user_id=args.user_id)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
