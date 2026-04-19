from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from app.models.internal_calendar import CalendarBlockStatus, CalendarBlockType, InternalCalendarBlockModel
from app.models.memory import MemorySource, MemoryType
from app.models.task import TaskModel, TaskStatus
from app.models.user import UserModel, UserPreferencesModel
from app.schemas.decision import DecisionNextBestActionRequest, DecisionPlanDayRequest, DecisionQueryRequest
from app.services.decision_service import DecisionService
from app.models.fatigue import FatigueEstimateModel, FatigueModeRecommendation, FatigueTimeBucket


class FakeTaskRepository:
    def __init__(self, tasks: list[TaskModel]) -> None:
        self.tasks = tasks
        self.calls: list[tuple[str, int]] = []

    def list_schedulable_tasks(self, *, user_id: str, task_ids: list[str] | None = None, limit: int = 100) -> list[TaskModel]:
        self.calls.append((user_id, limit))
        selected = [task for task in self.tasks if task.user_id == user_id]
        if task_ids:
            selected = [task for task in selected if task.id in task_ids]
        return selected[:limit]


class FakeCalendarRepository:
    def __init__(self, blocks: list[InternalCalendarBlockModel]) -> None:
        self.blocks = blocks

    def list_future_blocks(
        self,
        *,
        user_id: str,
        starts_after: datetime,
        ends_before: datetime | None = None,
        limit: int = 200,
    ) -> list[InternalCalendarBlockModel]:
        selected = [
            block for block in self.blocks
            if block.user_id == user_id
            and block.ends_at >= starts_after
            and (ends_before is None or block.starts_at <= ends_before)
        ]
        return selected[:limit]


class FakeUserRepository:
    def __init__(self, user: UserModel, preferences: UserPreferencesModel) -> None:
        self.user = user
        self.preferences = preferences

    def get_user(self, user_id: str) -> UserModel | None:
        return self.user if self.user.id == user_id else None

    def get_preferences(self, user_id: str) -> UserPreferencesModel | None:
        return self.preferences if self.preferences.user_id == user_id else None


class FakeFatigueService:
    def __init__(self, score: int, source: str = "pattern_estimate", confidence: float = 0.45) -> None:
        self.score = score
        self.source = source
        self.confidence = confidence
        self.calls: list[int | None] = []

    def estimate_current_fatigue(self, *, user_id: str, timezone_name: str | None = None, at: datetime | None = None) -> FatigueEstimateModel:
        _ = (user_id, timezone_name, at)
        self.calls.append(None)
        return FatigueEstimateModel(
            estimated_fatigue_score=float(self.score),
            time_bucket=FatigueTimeBucket.EVENING,
            pattern_confidence=self.confidence,
            estimation_confidence=self.confidence,
            mode_recommendation=FatigueModeRecommendation.DECISIVE if self.score >= 4 else FatigueModeRecommendation.GUIDED,
            source_mix={self.source: 1.0},
            reasons=[],
            explicit_checkin=None,
            matched_pattern=None,
        )


class FakeMemoryService:
    def __init__(self, memories: list[dict] | None = None) -> None:
        self.memories = memories or []
        self.calls: list[tuple[str, str | None, str | None, int]] = []
        self.normalized_queries: list[tuple[str | None, str | None]] = []

    def normalize_retrieval_query(self, *, query: str | None, domain: str | None = None) -> str | None:
        self.normalized_queries.append((query, domain))
        if query is None:
            return None
        return f"normalized::{query}"

    def get_relevant_memories(self, user_id: str, query: str | None, domain: str | None = None, limit: int = 5) -> list[dict]:
        self.calls.append((user_id, query, domain, limit))
        return self.memories[:limit]


def build_task(
    *,
    task_id: str,
    user_id: str = "user-1",
    due_in_hours: int | None = None,
    priority: int = 3,
    estimated_minutes: int | None = 30,
    energy_required: int | None = 3,
) -> TaskModel:
    now = datetime.now(UTC)
    return TaskModel(
        id=task_id,
        user_id=user_id,
        title=f"Task {task_id}",
        description=None,
        priority=priority,
        estimated_minutes=estimated_minutes,
        actual_minutes=None,
        energy_required=energy_required,
        due_at=(now + timedelta(hours=due_in_hours)) if due_in_hours is not None else None,
        status=TaskStatus.PENDING,
        source="user",
        metadata_json={},
        created_at=now,
        updated_at=now,
        completed_at=None,
    )


def build_block(*, task_id: str | None, starts_in_hours: int, duration_minutes: int = 30, user_id: str = "user-1") -> InternalCalendarBlockModel:
    now = datetime.now(UTC)
    starts_at = now + timedelta(hours=starts_in_hours)
    return InternalCalendarBlockModel(
        id=f"block-{task_id or 'free'}",
        user_id=user_id,
        task_id=task_id,
        title="Planned",
        block_type=CalendarBlockType.FOCUS_BLOCK,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=duration_minutes),
        status=CalendarBlockStatus.CONFIRMED,
        sync_to_google=False,
        external_event_id=None,
        source="system",
        reason_summary=None,
        reschedule_count=0,
        priority_snapshot=3,
        energy_snapshot=3,
        metadata_json={},
    )


def build_service(
    *,
    tasks: list[TaskModel],
    blocks: list[InternalCalendarBlockModel] | None = None,
    fatigue_score: int = 2,
    memories: list[dict] | None = None,
) -> tuple[DecisionService, FakeFatigueService, FakeTaskRepository, FakeMemoryService]:
    user = UserModel(
        id="user-1",
        auth_user_id="auth-1",
        email="user@example.com",
        full_name="User",
        timezone="UTC",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    preferences = UserPreferencesModel(
        id="pref-1",
        user_id="user-1",
        preferred_response_style="concise",
        fatigue_prompt_enabled=True,
    )
    task_repo = FakeTaskRepository(tasks)
    fatigue_service = FakeFatigueService(score=fatigue_score)
    memory_service = FakeMemoryService(memories)
    service = DecisionService(
        task_repository=task_repo,
        calendar_repository=FakeCalendarRepository(blocks or []),
        user_repository=FakeUserRepository(user, preferences),
        fatigue_service=fatigue_service,
        memory_service=memory_service,
    )
    return service, fatigue_service, task_repo, memory_service


def test_query_mode_changes_with_fatigue() -> None:
    tasks = [build_task(task_id="a", due_in_hours=8, priority=4, energy_required=2)]

    decisive_service, _, _, _ = build_service(tasks=tasks, fatigue_score=4)
    decisive = decisive_service.query(
        user_id="user-1",
        payload=DecisionQueryRequest(query="What should I do first tonight?"),
    )

    guided_service, _, _, _ = build_service(tasks=tasks, fatigue_score=2)
    guided = guided_service.query(
        user_id="user-1",
        payload=DecisionQueryRequest(query="What should I focus on next?"),
    )

    assert decisive.mode == "decisive"
    assert guided.mode == "guided"


def test_next_best_action_returns_one_recommendation() -> None:
    tasks = [
        build_task(task_id="a", due_in_hours=4, priority=4),
        build_task(task_id="b", due_in_hours=20, priority=3),
    ]
    service, _, _, _ = build_service(tasks=tasks, fatigue_score=5)

    response = service.next_best_action(
        user_id="user-1",
        payload=DecisionNextBestActionRequest(time_available_minutes=30),
    )

    assert response.primary_recommendation.task_id is not None
    assert response.alternatives == []


def test_scoring_prefers_nearer_deadline_when_other_factors_are_similar() -> None:
    tasks = [
        build_task(task_id="near", due_in_hours=6, priority=3, estimated_minutes=30, energy_required=2),
        build_task(task_id="later", due_in_hours=72, priority=3, estimated_minutes=30, energy_required=2),
    ]
    service, _, _, _ = build_service(tasks=tasks)

    response = service.query(
        user_id="user-1",
        payload=DecisionQueryRequest(query="What should I focus on next?"),
    )

    assert response.primary_recommendation.task_id == "near"


def test_high_energy_task_is_deprioritized_when_fatigue_is_high() -> None:
    tasks = [
        build_task(task_id="heavy", due_in_hours=24, priority=4, estimated_minutes=30, energy_required=5),
        build_task(task_id="light", due_in_hours=24, priority=4, estimated_minutes=30, energy_required=1),
    ]
    service, _, _, _ = build_service(tasks=tasks, fatigue_score=5)

    response = service.query(
        user_id="user-1",
        payload=DecisionQueryRequest(query="Can I handle this now?"),
    )

    assert response.primary_recommendation.task_id == "light"


def test_planned_soon_task_penalty_works() -> None:
    tasks = [
        build_task(task_id="planned", due_in_hours=24, priority=4, estimated_minutes=30, energy_required=2),
        build_task(task_id="free", due_in_hours=24, priority=4, estimated_minutes=30, energy_required=2),
    ]
    blocks = [build_block(task_id="planned", starts_in_hours=1)]
    service, _, _, _ = build_service(tasks=tasks, blocks=blocks, fatigue_score=2)

    response = service.query(
        user_id="user-1",
        payload=DecisionQueryRequest(query="What should I do first tonight?"),
    )

    assert response.primary_recommendation.task_id == "free"


def test_decision_flow_uses_normalized_memory_query_and_passes_retrieved_memories() -> None:
    tasks = [
        build_task(task_id="heavy", due_in_hours=24, priority=4, estimated_minutes=120, energy_required=5),
        build_task(task_id="light", due_in_hours=24, priority=4, estimated_minutes=30, energy_required=2),
    ]
    memories = [
        {
            "statement": "User often avoids demanding evening work",
            "confidence": 0.9,
            "metadata_json": {},
        }
    ]
    service, _, _, memory_service = build_service(tasks=tasks, fatigue_score=5, memories=memories)

    context = service.build_decision_context(
        user_id="user-1",
        query="Should I work on this tonight?",
        domain_hint="planning",
    )

    assert memory_service.normalized_queries == [("Should I work on this tonight?", "planning")]
    assert memory_service.calls == [("user-1", "normalized::Should I work on this tonight?", "planning", 5)]
    assert context.relevant_memories == memories


def test_owner_scoping_is_preserved() -> None:
    tasks = [
        build_task(task_id="mine", user_id="user-1", due_in_hours=10),
        build_task(task_id="other", user_id="user-2", due_in_hours=1),
    ]
    service, _, task_repo, _ = build_service(tasks=tasks)

    response = service.query(
        user_id="user-1",
        payload=DecisionQueryRequest(query="What should I focus on next?"),
    )

    assert response.primary_recommendation.task_id == "mine"
    assert task_repo.calls[0][0] == "user-1"


def test_explicit_fatigue_override_beats_pattern_estimate() -> None:
    tasks = [build_task(task_id="a", due_in_hours=6, priority=4, energy_required=2)]
    service, fatigue_service, _, _ = build_service(tasks=tasks, fatigue_score=1)

    response = service.query(
        user_id="user-1",
        payload=DecisionQueryRequest(query="What should I focus on next?", fatigue_score=5),
    )

    assert response.mode == "decisive"
    assert fatigue_service.calls == []


def test_empty_task_list_returns_clean_no_work_response() -> None:
    service, _, _, _ = build_service(tasks=[], fatigue_score=3)

    response = service.query(
        user_id="user-1",
        payload=DecisionQueryRequest(query="What now?"),
    )

    assert response.primary_recommendation.task_id is None
    assert "no active tasks" in response.reasoning_summary.lower()


def test_plan_day_returns_light_summary() -> None:
    tasks = [
        build_task(task_id="a", due_in_hours=8, priority=5, estimated_minutes=45, energy_required=2),
        build_task(task_id="b", due_in_hours=24, priority=4, estimated_minutes=30, energy_required=2),
    ]
    service, _, _, _ = build_service(tasks=tasks, fatigue_score=2)

    response = service.plan_day(
        user_id="user-1",
        payload=DecisionPlanDayRequest(date=date.today(), include_recommended_blocks=True),
    )

    assert response.recommendations
    assert response.summary


def test_decision_service_loads_memory_context_without_breaking_response() -> None:
    tasks = [
        build_task(task_id="short", due_in_hours=24, priority=4, estimated_minutes=30, energy_required=2),
        build_task(task_id="long", due_in_hours=24, priority=4, estimated_minutes=120, energy_required=2),
    ]
    service, _, _, memory_service = build_service(
        tasks=tasks,
        fatigue_score=2,
        memories=[
            {
                "id": "memory-1",
                "domain": "planning",
                "statement": "User prefers shorter focus blocks",
                "memory_type": MemoryType.PREFERENCE.value,
                "source": MemorySource.INFERRED.value,
                "confidence": 0.9,
                "metadata_json": {"preferred_duration_minutes": 45},
            }
        ],
    )

    response = service.query(
        user_id="user-1",
        payload=DecisionQueryRequest(query="What should I focus on next?", domain_hint="planning"),
    )

    assert response.primary_recommendation.task_id == "short"
    assert memory_service.calls[0][0] == "user-1"
    assert memory_service.calls[0][2] == "planning"
