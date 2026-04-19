from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from app.models.memory import LearnedMemoryModel, MemorySource, MemoryType
from app.services.memory_service import MemoryCandidate, MemoryService


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
            embedding=kwargs.get("embedding"),
            is_active=kwargs.get("is_active", True),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.memories.append(memory)
        return memory

    def update_memory(self, *, memory_id: str, user_id: str, values: dict) -> LearnedMemoryModel | None:
        for memory in self.memories:
            if memory.id == memory_id and memory.user_id == user_id:
                for key, value in values.items():
                    setattr(memory, key, value)
                memory.updated_at = datetime.now(UTC)
                return memory
        return None

    def get_memory(self, *, memory_id: str, user_id: str) -> LearnedMemoryModel | None:
        for memory in self.memories:
            if memory.id == memory_id and memory.user_id == user_id:
                return memory
        return None

    def find_active_memories_for_user(self, *, user_id: str, domain: str | None = None, limit: int = 50) -> list[LearnedMemoryModel]:
        items = [item for item in self.memories if item.user_id == user_id and item.is_active]
        if domain is not None:
            items = [item for item in items if item.domain == domain]
        return items[:limit]

    def find_possible_duplicate_memory(self, *, user_id: str, domain: str, statement: str) -> LearnedMemoryModel | None:
        normalized = " ".join(statement.lower().split())
        for memory in self.find_active_memories_for_user(user_id=user_id, domain=domain, limit=100):
            candidate = " ".join(memory.statement.lower().split())
            if candidate == normalized:
                return memory
        return None

    def list_recent_memories(self, *, user_id: str, limit: int = 20) -> list[LearnedMemoryModel]:
        items = [item for item in self.memories if item.user_id == user_id and item.is_active]
        return sorted(items, key=lambda item: item.updated_at or item.created_at or datetime.min.replace(tzinfo=UTC), reverse=True)[:limit]

    def get_relevant_memories(self, *, user_id: str, query: str | None, domain: str | None = None, limit: int = 5, embedding=None):
        _ = (query, embedding)
        return self.find_active_memories_for_user(user_id=user_id, domain=domain, limit=limit)


class NoopSignalRepository:
    def list_recent_interaction_events(self, **kwargs):
        _ = kwargs
        return []

    def list_feedback_for_distillation(self, **kwargs):
        _ = kwargs
        return []

    def list_checkins_for_aggregation(self, **kwargs):
        _ = kwargs
        return []

    def list_patterns_for_distillation(self, **kwargs):
        _ = kwargs
        return []


class MemoryServiceTests(unittest.TestCase):
    def build_service(self) -> tuple[MemoryService, InMemoryMemoryRepository]:
        memory_repository = InMemoryMemoryRepository()
        noop = NoopSignalRepository()
        service = MemoryService(
            connection=None,
            memory_repository=memory_repository,
            task_repository=noop,
            calendar_repository=noop,
            fatigue_repository=noop,
        )
        return service, memory_repository

    def test_memory_insert_and_update_behavior(self) -> None:
        service, repository = self.build_service()
        candidate = MemoryCandidate(
            user_id="user-1",
            memory_type=MemoryType.PREFERENCE,
            domain="planning",
            statement="User prefers shorter focus blocks",
            source=MemorySource.INFERRED,
            confidence=0.78,
            last_confirmed_at=datetime.now(UTC),
            metadata_json={"evidence_count": 2, "recent_examples_count": 2, "contradiction_count": 0},
        )

        created = service.upsert_memory(candidate=candidate)
        assert created is not None
        self.assertEqual(len(repository.memories), 1)

        stronger = MemoryCandidate(
            user_id="user-1",
            memory_type=MemoryType.PREFERENCE,
            domain="planning",
            statement="User prefers shorter focus blocks",
            source=MemorySource.INFERRED,
            confidence=0.91,
            last_confirmed_at=datetime.now(UTC) + timedelta(days=1),
            metadata_json={"evidence_count": 3, "recent_examples_count": 3, "contradiction_count": 0},
        )
        updated = service.upsert_memory(candidate=stronger)
        assert updated is not None

        self.assertEqual(len(repository.memories), 1)
        self.assertAlmostEqual(updated.confidence, 0.91, places=2)
        self.assertGreaterEqual(updated.metadata_json["evidence_count"], 3)

    def test_duplicate_memory_detection_merges_instead_of_creating_new_row(self) -> None:
        service, repository = self.build_service()
        first = MemoryCandidate(
            user_id="user-1",
            memory_type=MemoryType.PATTERN,
            domain="planning",
            statement="User often avoids demanding evening work",
            source=MemorySource.INFERRED,
            confidence=0.76,
            last_confirmed_at=datetime.now(UTC),
            metadata_json={"evidence_count": 2, "recent_examples_count": 2, "contradiction_count": 0},
        )
        second = MemoryCandidate(
            user_id="user-1",
            memory_type=MemoryType.PATTERN,
            domain="planning",
            statement="User   often avoids demanding evening work",
            source=MemorySource.INFERRED,
            confidence=0.82,
            last_confirmed_at=datetime.now(UTC),
            metadata_json={"evidence_count": 2, "recent_examples_count": 2, "contradiction_count": 0},
        )

        service.upsert_memory(candidate=first)
        service.upsert_memory(candidate=second)

        self.assertEqual(len(repository.memories), 1)

    def test_retrieval_returns_relevant_memories_and_excludes_inactive(self) -> None:
        service, repository = self.build_service()
        repository.create_memory(
            user_id="user-1",
            memory_type=MemoryType.PREFERENCE,
            domain="planning",
            statement="User prefers shorter focus blocks",
            source=MemorySource.INFERRED,
            confidence=0.88,
            last_confirmed_at=datetime.now(UTC),
            metadata_json={"evidence_count": 3},
            embedding=None,
            is_active=True,
        )
        repository.create_memory(
            user_id="user-1",
            memory_type=MemoryType.PATTERN,
            domain="planning",
            statement="User often avoids demanding evening work",
            source=MemorySource.INFERRED,
            confidence=0.8,
            last_confirmed_at=datetime.now(UTC),
            metadata_json={"evidence_count": 3},
            embedding=None,
            is_active=False,
        )

        results = service.get_relevant_memories("user-1", "short work block", domain="planning", limit=5)

        self.assertEqual(len(results), 1)
        self.assertIn("shorter focus blocks", results[0]["statement"].lower())

    def test_owner_scoping_is_preserved(self) -> None:
        service, repository = self.build_service()
        repository.create_memory(
            user_id="user-2",
            memory_type=MemoryType.PREFERENCE,
            domain="planning",
            statement="Other user memory",
            source=MemorySource.INFERRED,
            confidence=0.88,
            last_confirmed_at=datetime.now(UTC),
            metadata_json={"evidence_count": 3},
            embedding=None,
            is_active=True,
        )

        results = service.get_relevant_memories("user-1", "planning", domain="planning", limit=5)

        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
