from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from app.models.fatigue import FatigueCheckinModel, FatiguePatternModel, FatigueTimeBucket, FatigueTrendDirection
from app.models.memory import LearnedMemoryModel, MemorySource, MemoryType
from app.services.memory_service import MemoryService
from app.workers.jobs.memory_distillation import distill_memories_job


class InMemoryMemoryRepository:
    def __init__(self) -> None:
        self.memories: list[LearnedMemoryModel] = []

    def create_memory(self, **kwargs) -> LearnedMemoryModel:
        memory = LearnedMemoryModel(
            id=f"memory-{len(self.memories) + 1}",
            user_id=kwargs["user_id"],
            memory_type=kwargs["memory_type"],
            domain=kwargs["domain"],
            statement=kwargs["statement"],
            source=kwargs["source"],
            confidence=kwargs["confidence"],
            last_confirmed_at=kwargs["last_confirmed_at"],
            metadata_json=kwargs["metadata_json"],
            embedding=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            is_active=kwargs.get("is_active", True),
        )
        self.memories.append(memory)
        return memory

    def update_memory(self, *, memory_id: str, user_id: str, values: dict) -> LearnedMemoryModel | None:
        for memory in self.memories:
            if memory.id == memory_id and memory.user_id == user_id:
                for key, value in values.items():
                    setattr(memory, key, value)
                return memory
        return None

    def find_possible_duplicate_memory(self, *, user_id: str, domain: str, statement: str) -> LearnedMemoryModel | None:
        normalized = " ".join(statement.lower().split())
        for memory in self.memories:
            if memory.user_id == user_id and memory.domain == domain and " ".join(memory.statement.lower().split()) == normalized and memory.is_active:
                return memory
        return None

    def find_active_memories_for_user(self, *, user_id: str, domain: str | None = None, limit: int = 50):
        items = [item for item in self.memories if item.user_id == user_id and item.is_active]
        if domain is not None:
            items = [item for item in items if item.domain == domain]
        return items[:limit]

    def list_recent_memories(self, *, user_id: str, limit: int = 20):
        return self.find_active_memories_for_user(user_id=user_id, limit=limit)

    def get_relevant_memories(self, *, user_id: str, query: str | None, domain: str | None = None, limit: int = 5, embedding=None):
        _ = (query, embedding)
        return self.find_active_memories_for_user(user_id=user_id, domain=domain, limit=limit)


class FakeTaskRepository:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def list_recent_interaction_events(self, *, user_id: str, since: datetime, limit: int = 200):
        return [row for row in self.rows if row["user_id"] == user_id and row["created_at"] >= since][:limit]


class FakeCalendarRepository:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def list_feedback_for_distillation(self, *, user_id: str, since: datetime, limit: int = 200):
        return [row for row in self.rows if row["user_id"] == user_id and row["created_at"] >= since][:limit]


class FakeFatigueRepository:
    def __init__(self, checkins: list[FatigueCheckinModel], patterns: list[FatiguePatternModel]) -> None:
        self.checkins = checkins
        self.patterns = patterns

    def list_checkins_for_aggregation(self, *, user_id: str | None = None, since: datetime | None = None):
        items = self.checkins
        if user_id is not None:
            items = [item for item in items if item.user_id == user_id]
        if since is not None:
            items = [item for item in items if (item.created_at or datetime.min.replace(tzinfo=UTC)) >= since]
        return items

    def list_patterns_for_distillation(self, *, user_id: str, min_confidence: float = 0.0, limit: int = 50):
        items = [item for item in self.patterns if item.user_id == user_id and item.confidence >= min_confidence]
        return items[:limit]


class MemoryDistillationTests(unittest.TestCase):
    def build_service(
        self,
        *,
        interaction_rows: list[dict] | None = None,
        feedback_rows: list[dict] | None = None,
        patterns: list[FatiguePatternModel] | None = None,
    ) -> tuple[MemoryService, InMemoryMemoryRepository]:
        memory_repository = InMemoryMemoryRepository()
        service = MemoryService(
            connection=None,
            memory_repository=memory_repository,
            task_repository=FakeTaskRepository(interaction_rows or []),
            calendar_repository=FakeCalendarRepository(feedback_rows or []),
            fatigue_repository=FakeFatigueRepository([], patterns or []),
        )
        return service, memory_repository

    def test_distillation_from_repeated_calendar_feedback(self) -> None:
        base = datetime(2026, 4, 19, 18, 0, tzinfo=UTC)
        feedback = [
            {
                "id": "f1",
                "calendar_block_id": "b1",
                "user_id": "user-1",
                "response_type": "rejected",
                "reason_code": "too_tired",
                "reason_text": None,
                "fatigue_score": 4,
                "created_at": base,
                "starts_at": base,
                "ends_at": base + timedelta(minutes=60),
                "duration_minutes": 60,
            },
            {
                "id": "f2",
                "calendar_block_id": "b2",
                "user_id": "user-1",
                "response_type": "moved",
                "reason_code": "too_tired",
                "reason_text": None,
                "fatigue_score": 5,
                "created_at": base + timedelta(days=1),
                "starts_at": base + timedelta(days=1),
                "ends_at": base + timedelta(days=1, minutes=60),
                "duration_minutes": 60,
            },
        ]
        service, repository = self.build_service(feedback_rows=feedback)

        stored = service.distill_memories_for_user(user_id="user-1", days_back=30, as_of=base + timedelta(days=2))

        self.assertTrue(any("evening work" in item.statement.lower() for item in stored))
        self.assertEqual(len(repository.memories), 1)

    def test_distillation_from_fatigue_patterns_and_interaction_evidence(self) -> None:
        base = datetime(2026, 4, 19, 10, 0, tzinfo=UTC)
        interaction_rows = [
            {
                "id": "e1",
                "user_id": "user-1",
                "event_type": "suggestion_accepted",
                "entity_type": "internal_calendar",
                "entity_id": "b1",
                "payload_json": {"fatigue_score": 4},
                "created_at": base,
            },
            {
                "id": "e2",
                "user_id": "user-1",
                "event_type": "suggestion_completed",
                "entity_type": "internal_calendar",
                "entity_id": "b2",
                "payload_json": {"fatigue_score": 5},
                "created_at": base + timedelta(days=1),
            },
        ]
        patterns = [
            FatiguePatternModel(
                id="p1",
                user_id="user-1",
                weekday=6,
                time_bucket=FatigueTimeBucket.EVENING,
                avg_fatigue=4.2,
                min_fatigue=3.8,
                max_fatigue=4.8,
                fatigue_variance=0.3,
                sample_count=4,
                confidence=0.8,
                trend_direction=FatigueTrendDirection.STABLE,
                last_signal_at=base,
                last_computed_at=base,
                metadata_json={},
            )
        ]
        service, repository = self.build_service(interaction_rows=interaction_rows, patterns=patterns)

        stored = service.distill_memories_for_user(user_id="user-1", days_back=30, as_of=base + timedelta(days=2))

        statements = [item.statement for item in stored]
        self.assertIn("User prefers direct suggestions when tired", statements)
        self.assertEqual(len(repository.memories), 1)

    def test_rejection_at_night_requires_repeated_evidence(self) -> None:
        base = datetime(2026, 4, 19, 21, 0, tzinfo=UTC)
        service, repository = self.build_service(
            feedback_rows=[
                {
                    "id": "f1",
                    "calendar_block_id": "b1",
                    "user_id": "user-1",
                    "response_type": "rejected",
                    "reason_code": "too_tired",
                    "reason_text": None,
                    "fatigue_score": 5,
                    "created_at": base,
                    "starts_at": base,
                    "ends_at": base + timedelta(minutes=30),
                    "duration_minutes": 30,
                }
            ]
        )

        stored = service.distill_memories_for_user(user_id="user-1", days_back=30, as_of=base + timedelta(days=1))

        self.assertEqual(stored, [])
        self.assertEqual(repository.memories, [])

    def test_one_off_event_does_not_become_memory(self) -> None:
        base = datetime(2026, 4, 19, 9, 0, tzinfo=UTC)
        service, repository = self.build_service(
            interaction_rows=[
                {
                    "id": "e1",
                    "user_id": "user-1",
                    "event_type": "suggestion_accepted",
                    "entity_type": "internal_calendar",
                    "entity_id": "b1",
                    "payload_json": {"fatigue_score": 4},
                    "created_at": base,
                }
            ]
        )

        stored = service.distill_memories_for_user(user_id="user-1", days_back=30, as_of=base + timedelta(days=1))

        self.assertEqual(stored, [])
        self.assertEqual(repository.memories, [])

    def test_worker_job_supports_target_user_scope(self) -> None:
        class FakeConnection:
            def close(self) -> None:
                return None

        class FakeMemoryService:
            def __init__(self, connection) -> None:
                _ = connection

            def distill_memories_for_user(self, *, user_id: str, days_back: int, as_of: datetime):
                _ = (days_back, as_of)
                return [
                    LearnedMemoryModel(
                        id="m1",
                        user_id=user_id,
                        memory_type=MemoryType.PATTERN,
                        domain="planning",
                        statement="User often avoids demanding evening work",
                        source=MemorySource.INFERRED,
                        confidence=0.82,
                        last_confirmed_at=as_of,
                        metadata_json={},
                    )
                ]

        from unittest.mock import patch

        with patch("app.workers.jobs.memory_distillation.MemoryService", FakeMemoryService), patch(
            "app.workers.jobs.memory_distillation._log_memory_event"
        ) as log_event:
            result = distill_memories_job(
                user_id="user-1",
                days_back=30,
                connection=FakeConnection(),
                as_of=datetime(2026, 4, 20, 10, 0, tzinfo=UTC),
            )

        self.assertEqual(result["user_count"], 1)
        self.assertEqual(result["memory_count"], 1)
        log_event.assert_called_once()


if __name__ == "__main__":
    unittest.main()
