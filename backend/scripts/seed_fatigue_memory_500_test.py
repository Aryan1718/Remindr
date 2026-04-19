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
from app.repositories.fatigue import FatigueRepository
from app.repositories.memories import MemoryRepository
from app.schemas.fatigue import FatigueCheckinCreateRequest, FatiguePatternFilters
from app.workers.jobs.fatigue_aggregation import recompute_fatigue_patterns_job


@dataclass(slots=True)
class FatigueSeed:
    score: int
    created_at: datetime
    notes: str
    context_json: dict[str, object]
    source: str = "seed_500_script"


def build_seeds(*, now: datetime, row_count: int) -> list[FatigueSeed]:
    seeds: list[FatigueSeed] = []
    base_day = now.replace(minute=0, second=0, microsecond=0) - timedelta(days=row_count // 4)

    for index in range(row_count):
        day = base_day + timedelta(days=index // 4)
        slot = index % 4

        if slot == 0:
            created_at = day.replace(hour=8, minute=0)
            score = 1
            label = "morning"
            notes = "Seeded strong morning energy"
        elif slot == 1:
            created_at = day.replace(hour=14, minute=0)
            score = 5
            label = "afternoon"
            notes = "Seeded strong afternoon fatigue"
        elif slot == 2:
            created_at = day.replace(hour=19, minute=0)
            score = 4
            label = "evening"
            notes = "Seeded strong evening fatigue"
        else:
            created_at = day.replace(hour=21, minute=0)
            score = 5
            label = "night"
            notes = "Seeded strong night fatigue"

        if index % 9 == 4:
            created_at = created_at + timedelta(minutes=30)

        seeds.append(
            FatigueSeed(
                score=score,
                created_at=created_at,
                notes=f"{notes} #{index + 1}",
                context_json={
                    "bulk_seed": True,
                    "slot": label,
                    "seed_index": index + 1,
                    "target_memory": True,
                },
            )
        )

    return seeds


def seed_checkins(*, connection: psycopg.Connection, user_id: str, seeds: list[FatigueSeed]) -> list[str]:
    repository = FatigueRepository(connection)
    checkin_ids: list[str] = []
    for seed in seeds:
        checkin = repository.create_checkin(
            user_id=user_id,
            payload=FatigueCheckinCreateRequest(
                score=seed.score,
                source=seed.source,
                notes=seed.notes,
                context_json=seed.context_json,
                created_at=seed.created_at,
            ),
        )
        checkin_ids.append(checkin.id)
    return checkin_ids


def print_patterns(*, connection: psycopg.Connection, user_id: str) -> None:
    repository = FatigueRepository(connection)
    patterns = repository.list_patterns(user_id=user_id, filters=FatiguePatternFilters(limit=20))
    print("\nFatigue patterns:")
    if not patterns:
        print("  none")
        return
    for pattern in patterns:
        print(
            "  - "
            f"weekday={pattern.weekday} "
            f"bucket={pattern.time_bucket.value} "
            f"avg={pattern.avg_fatigue} "
            f"confidence={pattern.confidence} "
            f"samples={pattern.sample_count}"
        )


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
        description="Seed 500 raw fatigue_checkins rows and invoke aggregation plus memory distillation."
    )
    parser.add_argument("--user-id", required=True, help="Target user id")
    parser.add_argument(
        "--row-count",
        default=500,
        type=int,
        help="Number of raw fatigue_checkins rows to insert",
    )
    parser.add_argument(
        "--days-back",
        default=365,
        type=int,
        help="Aggregation lookback window passed to recompute_fatigue_patterns_job",
    )
    parser.add_argument(
        "--skip-worker",
        action="store_true",
        help="Only insert raw fatigue_checkins and skip invoking the worker flow",
    )
    args = parser.parse_args()

    now = datetime.now(UTC)
    seeds = build_seeds(now=now, row_count=args.row_count)
    database_url = get_database_url()

    with connect_db(database_url=database_url) as connection:
        checkin_ids = seed_checkins(connection=connection, user_id=args.user_id, seeds=seeds)
        print(f"Inserted {len(checkin_ids)} raw fatigue_checkins rows for user {args.user_id}.")
        print(f"First 10 checkin ids: {', '.join(checkin_ids[:10])}")

        if not args.skip_worker:
            patterns = recompute_fatigue_patterns_job(
                database_url=database_url,
                user_id=args.user_id,
                days_back=args.days_back,
            )
            print(f"Recomputed {len(patterns)} fatigue pattern rows.")

        print_patterns(connection=connection, user_id=args.user_id)
        print_recent_memories(connection=connection, user_id=args.user_id)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
