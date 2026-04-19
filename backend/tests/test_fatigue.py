from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from pydantic import ValidationError

from app.models.fatigue import (
    FatigueCheckinModel,
    FatiguePatternModel,
    FatigueTimeBucket,
    FatigueTrendDirection,
)
from app.schemas.fatigue import FatigueCheckinCreateRequest, FatigueCheckinListFilters, FatiguePatternRecomputeRequest
from app.services.fatigue_service import FatigueService, bucket_for_datetime
from app.workers.jobs.fatigue_aggregation import FatigueAggregationWorker


class InMemoryFatigueRepository:
    def __init__(self) -> None:
        self.checkins: list[FatigueCheckinModel] = []
        self.patterns: dict[tuple[str, int, FatigueTimeBucket], FatiguePatternModel] = {}
        self.timezones: dict[str, str] = {}
        self.logged_events: list[dict] = []

    def create_checkin(self, *, user_id: str, payload: FatigueCheckinCreateRequest) -> FatigueCheckinModel:
        checkin = FatigueCheckinModel(
            id=f"checkin-{len(self.checkins) + 1}",
            user_id=user_id,
            score=payload.score,
            source=payload.source,
            notes=payload.notes,
            context_json=payload.context_json,
            created_at=payload.created_at or datetime.now(UTC),
        )
        self.checkins.append(checkin)
        return checkin

    def list_checkins(self, *, user_id: str, limit: int = 20) -> list[FatigueCheckinModel]:
        items = [item for item in self.checkins if item.user_id == user_id]
        return sorted(items, key=lambda item: item.created_at or datetime.min.replace(tzinfo=UTC), reverse=True)[:limit]

    def get_recent_checkin(self, *, user_id: str, since: datetime) -> FatigueCheckinModel | None:
        for item in self.list_checkins(user_id=user_id, limit=100):
            if item.created_at and item.created_at >= since:
                return item
        return None

    def list_patterns(self, *, user_id: str, filters) -> list[FatiguePatternModel]:
        items = [pattern for key, pattern in self.patterns.items() if key[0] == user_id]
        if filters.weekday is not None:
            items = [pattern for pattern in items if pattern.weekday == filters.weekday]
        if filters.time_bucket is not None:
            items = [pattern for pattern in items if pattern.time_bucket == filters.time_bucket]
        return items[: filters.limit]

    def get_pattern(self, *, user_id: str, weekday: int, time_bucket: FatigueTimeBucket) -> FatiguePatternModel | None:
        return self.patterns.get((user_id, weekday, time_bucket))

    def get_user_timezone(self, *, user_id: str) -> str | None:
        return self.timezones.get(user_id)

    def list_checkins_for_aggregation(self, *, user_id: str | None = None, since: datetime | None = None) -> list[FatigueCheckinModel]:
        items = self.checkins
        if user_id is not None:
            items = [item for item in items if item.user_id == user_id]
        if since is not None:
            items = [item for item in items if item.created_at and item.created_at >= since]
        return items

    def upsert_patterns(self, patterns: list[FatiguePatternModel]) -> list[FatiguePatternModel]:
        for pattern in patterns:
            key = (pattern.user_id, pattern.weekday, pattern.time_bucket)
            existing = self.patterns.get(key)
            pattern.id = existing.id if existing else f"pattern-{len(self.patterns) + 1}"
            self.patterns[key] = pattern
        return patterns

    def log_event(self, *, user_id: str, event_type: str, entity_id: str | None = None, payload=None) -> str:
        self.logged_events.append(
            {"user_id": user_id, "event_type": event_type, "entity_id": entity_id, "payload": payload or {}}
        )
        return f"event-{len(self.logged_events)}"


class FatigueServiceTests(unittest.TestCase):
    def test_create_checkin_success(self) -> None:
        repository = InMemoryFatigueRepository()
        service = FatigueService(connection=None, repository=repository)

        checkin = service.create_checkin(
            user_id="user-1",
            payload=FatigueCheckinCreateRequest(score=4, notes="Low energy"),
        )

        self.assertEqual(checkin.score, 4)
        self.assertEqual(checkin.user_id, "user-1")
        self.assertEqual(repository.logged_events[0]["event_type"], "fatigue_checkin_submitted")

    def test_invalid_score_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            FatigueCheckinCreateRequest(score=6)

    def test_list_checkins_is_owner_scoped(self) -> None:
        repository = InMemoryFatigueRepository()
        service = FatigueService(connection=None, repository=repository)
        now = datetime.now(UTC)
        repository.create_checkin(
            user_id="user-1",
            payload=FatigueCheckinCreateRequest(score=2, created_at=now),
        )
        repository.create_checkin(
            user_id="user-2",
            payload=FatigueCheckinCreateRequest(score=5, created_at=now - timedelta(minutes=10)),
        )

        items = service.list_checkins(user_id="user-1", filters=FatigueCheckinListFilters(limit=20))

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].user_id, "user-1")

    def test_estimation_mode_uses_recent_checkin_and_pattern(self) -> None:
        repository = InMemoryFatigueRepository()
        repository.timezones["user-1"] = "America/Los_Angeles"
        now = datetime(2026, 4, 19, 18, 30, tzinfo=UTC)
        repository.create_checkin(
            user_id="user-1",
            payload=FatigueCheckinCreateRequest(score=5, created_at=now - timedelta(hours=1)),
        )
        repository.patterns[("user-1", 6, FatigueTimeBucket.MORNING)] = FatiguePatternModel(
            id="pattern-1",
            user_id="user-1",
            weekday=6,
            time_bucket=FatigueTimeBucket.MORNING,
            avg_fatigue=4.0,
            min_fatigue=3.0,
            max_fatigue=5.0,
            fatigue_variance=0.5,
            sample_count=4,
            confidence=0.75,
            trend_direction=FatigueTrendDirection.STABLE,
            last_signal_at=now - timedelta(days=1),
            last_computed_at=now - timedelta(hours=2),
            metadata_json={},
        )
        service = FatigueService(connection=None, repository=repository)

        estimate = service.estimate_current_fatigue(user_id="user-1", at=now)

        self.assertEqual(estimate.time_bucket, FatigueTimeBucket.MORNING)
        self.assertEqual(estimate.mode_recommendation.value, "decisive")
        self.assertAlmostEqual(estimate.estimated_fatigue_score, 4.6, places=2)


class FatigueAggregationTests(unittest.TestCase):
    def test_time_bucket_mapping(self) -> None:
        self.assertEqual(bucket_for_datetime(datetime(2026, 1, 1, 5, 0, tzinfo=UTC)), FatigueTimeBucket.MORNING)
        self.assertEqual(bucket_for_datetime(datetime(2026, 1, 1, 12, 0, tzinfo=UTC)), FatigueTimeBucket.AFTERNOON)
        self.assertEqual(bucket_for_datetime(datetime(2026, 1, 1, 17, 0, tzinfo=UTC)), FatigueTimeBucket.EVENING)
        self.assertEqual(bucket_for_datetime(datetime(2026, 1, 1, 3, 59, tzinfo=UTC)), FatigueTimeBucket.NIGHT)

    def test_recompute_patterns_creates_and_updates_bucket_rows(self) -> None:
        repository = InMemoryFatigueRepository()
        repository.timezones["user-1"] = "UTC"
        service = FatigueService(connection=None, repository=repository)
        now = datetime(2026, 4, 20, 15, 0, tzinfo=UTC)

        service.create_checkin(
            user_id="user-1",
            payload=FatigueCheckinCreateRequest(score=4, created_at=now - timedelta(days=7)),
        )
        service.create_checkin(
            user_id="user-1",
            payload=FatigueCheckinCreateRequest(score=2, created_at=now - timedelta(days=14)),
        )

        worker = FatigueAggregationWorker(repository)
        first_run = worker.recompute_patterns(user_id="user-1", days_back=30, as_of=now)
        self.assertEqual(len(first_run), 1)
        self.assertEqual(first_run[0].sample_count, 2)

        service.create_checkin(
            user_id="user-1",
            payload=FatigueCheckinCreateRequest(score=5, created_at=now - timedelta(days=21)),
        )
        second_run = worker.recompute_patterns(user_id="user-1", days_back=30, as_of=now)

        self.assertEqual(len(second_run), 1)
        self.assertEqual(len(repository.patterns), 1)
        updated = second_run[0]
        self.assertEqual(updated.sample_count, 3)
        self.assertAlmostEqual(updated.avg_fatigue, 3.67, places=2)


if __name__ == "__main__":
    unittest.main()
