from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.external_calendar_event import ExternalCalendarEventModel
from app.models.fatigue import FatiguePatternModel, FatigueTimeBucket, FatigueTrendDirection
from app.models.internal_calendar import CalendarBlockStatus, CalendarBlockType, InternalCalendarBlockModel
from app.models.task import TaskModel, TaskStatus
from app.models.user import UserModel, UserPreferencesModel
from app.schemas.internal_calendar import InternalCalendarSuggestRequest
from app.services.internal_calendar_service import InternalCalendarService
from app.workers.watchers.deadline_watcher import DeadlineWatcher


class FakeTaskRepository:
    def __init__(self, tasks: list[TaskModel]) -> None:
        self.tasks = tasks
        self.logged_events: list[dict] = []

    def list_schedulable_tasks(self, *, user_id: str, task_ids: list[str] | None = None, limit: int = 100) -> list[TaskModel]:
        selected = [
            task for task in self.tasks
            if task.user_id == user_id and task.status in {TaskStatus.PENDING, TaskStatus.SCHEDULED, TaskStatus.IN_PROGRESS}
        ]
        if task_ids:
            selected = [task for task in selected if task.id in task_ids]
        return selected[:limit]

    def list_deadline_watch_candidates(self, *, due_before: datetime, user_id: str | None = None, limit: int = 200) -> list[TaskModel]:
        selected = [
            task for task in self.tasks
            if task.due_at is not None
            and task.due_at <= due_before
            and (user_id is None or task.user_id == user_id)
        ]
        return selected[:limit]

    def log_task_event(self, *, user_id: str, event_type: str, task_id: str, payload=None) -> None:
        self.logged_events.append(
            {"user_id": user_id, "event_type": event_type, "task_id": task_id, "payload": payload or {}}
        )


class FakeInternalCalendarRepository:
    def __init__(self, blocks: list[InternalCalendarBlockModel] | None = None) -> None:
        self.blocks = list(blocks or [])
        self.window_calls: list[str] = []
        self.created_blocks: list[InternalCalendarBlockModel] = []

    def list_blocks_in_window(
        self,
        *,
        user_id: str,
        window_start: datetime,
        window_end: datetime,
        exclude_block_id: str | None = None,
    ) -> list[InternalCalendarBlockModel]:
        self.window_calls.append(user_id)
        items = []
        for block in self.blocks:
            if block.user_id != user_id:
                continue
            if exclude_block_id is not None and block.id == exclude_block_id:
                continue
            if block.starts_at < window_end and block.ends_at > window_start:
                items.append(block)
        return sorted(items, key=lambda block: (block.starts_at, block.ends_at))

    def list_task_blocks_in_window(
        self,
        *,
        user_id: str,
        task_id: str,
        window_start: datetime,
        window_end: datetime,
    ) -> list[InternalCalendarBlockModel]:
        return [
            block for block in self.list_blocks_in_window(user_id=user_id, window_start=window_start, window_end=window_end)
            if block.task_id == task_id
        ]

    def create_block(
        self,
        *,
        user_id: str,
        task_id: str | None,
        title: str,
        block_type: CalendarBlockType,
        starts_at: datetime,
        ends_at: datetime,
        status: CalendarBlockStatus,
        sync_to_google: bool,
        source: str,
        reason_summary: str | None,
        priority_snapshot: int | None,
        energy_snapshot: int | None,
        metadata_json,
    ) -> InternalCalendarBlockModel:
        block = InternalCalendarBlockModel(
            id=f"block-{len(self.blocks) + 1}",
            user_id=user_id,
            task_id=task_id,
            title=title,
            block_type=block_type,
            starts_at=starts_at,
            ends_at=ends_at,
            status=status,
            sync_to_google=sync_to_google,
            external_event_id=None,
            source=source,
            reason_summary=reason_summary,
            reschedule_count=0,
            priority_snapshot=priority_snapshot,
            energy_snapshot=energy_snapshot,
            metadata_json=metadata_json or {},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.blocks.append(block)
        self.created_blocks.append(block)
        return block

    def log_calendar_event(self, *, user_id: str, event_type: str, block_id: str, payload=None) -> None:
        _ = (user_id, event_type, block_id, payload)


class FakeConnectorRepository:
    def __init__(self, events: list[ExternalCalendarEventModel] | None = None) -> None:
        self.events = list(events or [])
        self.calls: list[str] = []

    def list_external_calendar_events(self, *, user_id: str, start: datetime, end: datetime) -> list[ExternalCalendarEventModel]:
        self.calls.append(user_id)
        return [
            event for event in self.events
            if event.user_id == user_id and event.starts_at < end and event.ends_at > start
        ]


class FakeFatigueRepository:
    def __init__(self, patterns: list[FatiguePatternModel] | None = None) -> None:
        self.patterns = {
            (pattern.user_id, pattern.weekday, pattern.time_bucket): pattern
            for pattern in (patterns or [])
        }

    def get_pattern(self, *, user_id: str, weekday: int, time_bucket: FatigueTimeBucket):
        return self.patterns.get((user_id, weekday, time_bucket))


class FakeUserRepository:
    def __init__(self, users: list[UserModel], preferences: list[UserPreferencesModel]) -> None:
        self.users = {user.id: user for user in users}
        self.preferences = {pref.user_id: pref for pref in preferences}

    def get_user(self, user_id: str) -> UserModel | None:
        return self.users.get(user_id)

    def get_preferences(self, user_id: str) -> UserPreferencesModel | None:
        return self.preferences.get(user_id)


def build_user(*, user_id: str = "user-1", timezone_name: str = "UTC") -> UserModel:
    return UserModel(
        id=user_id,
        auth_user_id=f"auth-{user_id}",
        email=f"{user_id}@example.com",
        full_name=user_id,
        timezone=timezone_name,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def build_preferences(*, user_id: str = "user-1") -> UserPreferencesModel:
    return UserPreferencesModel(
        id=f"pref-{user_id}",
        user_id=user_id,
        work_start_time="08:00:00",
        work_end_time="18:00:00",
        work_days=[1, 2, 3, 4, 5, 6, 7],
    )


def build_task(
    *,
    task_id: str,
    user_id: str = "user-1",
    due_at: datetime | None = None,
    estimated_minutes: int = 60,
    priority: int = 3,
    energy_required: int | None = 3,
    status: TaskStatus = TaskStatus.PENDING,
) -> TaskModel:
    now = datetime.now(timezone.utc)
    return TaskModel(
        id=task_id,
        user_id=user_id,
        title=f"Task {task_id}",
        description=None,
        priority=priority,
        estimated_minutes=estimated_minutes,
        actual_minutes=None,
        energy_required=energy_required,
        due_at=due_at,
        status=status,
        source="user",
        metadata_json={},
        created_at=now,
        updated_at=now,
        completed_at=None,
    )


def build_block(
    *,
    block_id: str,
    starts_at: datetime,
    ends_at: datetime,
    user_id: str = "user-1",
    task_id: str | None = None,
    status: CalendarBlockStatus = CalendarBlockStatus.CONFIRMED,
) -> InternalCalendarBlockModel:
    return InternalCalendarBlockModel(
        id=block_id,
        user_id=user_id,
        task_id=task_id,
        title="Planned",
        block_type=CalendarBlockType.SUGGESTED_TASK,
        starts_at=starts_at,
        ends_at=ends_at,
        status=status,
        sync_to_google=False,
        external_event_id=None,
        source="system",
        reason_summary=None,
        reschedule_count=0,
        priority_snapshot=3,
        energy_snapshot=3,
        metadata_json={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def build_external_event(
    *,
    event_id: str,
    starts_at: datetime,
    ends_at: datetime,
    user_id: str = "user-1",
) -> ExternalCalendarEventModel:
    return ExternalCalendarEventModel(
        id=event_id,
        user_id=user_id,
        connector_id="connector-1",
        external_event_id=event_id,
        calendar_id="primary",
        title="Meeting",
        description=None,
        location=None,
        starts_at=starts_at,
        ends_at=ends_at,
        is_all_day=False,
        status="confirmed",
        raw_payload_json={},
        last_synced_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def build_service(
    *,
    tasks: list[TaskModel],
    blocks: list[InternalCalendarBlockModel] | None = None,
    events: list[ExternalCalendarEventModel] | None = None,
    patterns: list[FatiguePatternModel] | None = None,
    users: list[UserModel] | None = None,
    preferences: list[UserPreferencesModel] | None = None,
) -> tuple[InternalCalendarService, FakeInternalCalendarRepository, FakeConnectorRepository, FakeTaskRepository]:
    user_rows = users or [build_user()]
    preference_rows = preferences or [build_preferences(user_id=user_rows[0].id)]
    task_repo = FakeTaskRepository(tasks)
    calendar_repo = FakeInternalCalendarRepository(blocks)
    connector_repo = FakeConnectorRepository(events)
    service = InternalCalendarService(
        repository=calendar_repo,
        task_repository=task_repo,
        fatigue_repository=FakeFatigueRepository(patterns),
        connector_repository=connector_repo,
        user_repository=FakeUserRepository(user_rows, preference_rows),
    )
    return service, calendar_repo, connector_repo, task_repo


def test_scheduling_avoids_overlap_with_external_calendar_event() -> None:
    base = datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc)
    task = build_task(task_id="urgent", due_at=base + timedelta(hours=8))
    event = build_external_event(event_id="event-1", starts_at=base, ends_at=base + timedelta(hours=1))
    service, calendar_repo, _, _ = build_service(tasks=[task], events=[event])

    suggestions = service.suggest_blocks(
        user_id="user-1",
        payload=InternalCalendarSuggestRequest(
            task_ids=["urgent"],
            window_start=base,
            window_end=base + timedelta(hours=4),
            max_suggestions=1,
        ),
    )

    assert len(suggestions) == 1
    assert suggestions[0].starts_at == base + timedelta(hours=1)
    assert calendar_repo.created_blocks[0].starts_at >= event.ends_at


def test_scheduling_avoids_overlap_with_existing_internal_block() -> None:
    base = datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc)
    task = build_task(task_id="task-1", due_at=base + timedelta(hours=8))
    existing = build_block(
        block_id="existing",
        starts_at=base,
        ends_at=base + timedelta(hours=1),
        task_id="other-task",
    )
    service, _, _, _ = build_service(tasks=[task], blocks=[existing])

    suggestions = service.suggest_blocks(
        user_id="user-1",
        payload=InternalCalendarSuggestRequest(
            task_ids=["task-1"],
            window_start=base,
            window_end=base + timedelta(hours=4),
            max_suggestions=1,
        ),
    )

    assert len(suggestions) == 1
    assert suggestions[0].starts_at == base + timedelta(hours=1)
    assert suggestions[0].starts_at >= existing.ends_at


def test_free_window_generation_returns_expected_gaps() -> None:
    base = datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc)
    event = build_external_event(event_id="event-1", starts_at=base + timedelta(hours=1), ends_at=base + timedelta(hours=2))
    block = build_block(
        block_id="block-1",
        starts_at=base + timedelta(hours=3),
        ends_at=base + timedelta(hours=4),
        task_id="task-a",
    )
    service, _, _, _ = build_service(tasks=[], blocks=[block], events=[event])

    free_windows = service.get_candidate_free_windows(
        user_id="user-1",
        window_start=base,
        window_end=base + timedelta(hours=5),
    )

    actual = [(window.starts_at, window.ends_at) for window in free_windows]
    assert actual == [
        (base, base + timedelta(hours=1)),
        (base + timedelta(hours=2), base + timedelta(hours=3)),
        (base + timedelta(hours=4), base + timedelta(hours=5)),
    ]


def test_two_external_events_block_internal_scheduling_without_creating_internal_copies() -> None:
    base = datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc)
    task = build_task(task_id="task-1", due_at=base + timedelta(hours=8), estimated_minutes=60)
    events = [
        build_external_event(
            event_id="event-1",
            starts_at=base + timedelta(hours=1),
            ends_at=base + timedelta(hours=2),
        ),
        build_external_event(
            event_id="event-2",
            starts_at=base + timedelta(hours=3),
            ends_at=base + timedelta(hours=4),
        ),
    ]
    service, calendar_repo, external_repo, _ = build_service(tasks=[task], events=events)

    suggestions = service.suggest_blocks(
        user_id="user-1",
        payload=InternalCalendarSuggestRequest(
            task_ids=["task-1"],
            window_start=base,
            window_end=base + timedelta(hours=5),
            max_suggestions=1,
        ),
    )

    assert external_repo.calls == ["user-1"]
    assert len(calendar_repo.created_blocks) == 1
    assert calendar_repo.created_blocks[0].external_event_id is None
    assert suggestions[0].starts_at == base + timedelta(hours=2)
    assert suggestions[0].ends_at == base + timedelta(hours=3)
    assert all(
        not (suggestions[0].starts_at < event.ends_at and suggestions[0].ends_at > event.starts_at)
        for event in events
    )
    assert all(block.id not in {"event-1", "event-2"} for block in calendar_repo.created_blocks)


def test_candidate_scoring_prefers_earlier_better_fitting_window_for_urgent_task() -> None:
    base = datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc)
    due_at = base + timedelta(hours=2)
    task = build_task(task_id="task-1", due_at=due_at, estimated_minutes=30, priority=5)
    blocking_events = [
        build_external_event(event_id="event-a", starts_at=base + timedelta(minutes=30), ends_at=base + timedelta(hours=1)),
        build_external_event(event_id="event-b", starts_at=base + timedelta(hours=1, minutes=30), ends_at=base + timedelta(hours=2)),
    ]
    service, _, _, _ = build_service(tasks=[task], events=blocking_events)

    suggestions = service.suggest_blocks(
        user_id="user-1",
        payload=InternalCalendarSuggestRequest(
            task_ids=["task-1"],
            window_start=base,
            window_end=due_at,
            max_suggestions=1,
        ),
    )

    assert len(suggestions) == 1
    assert suggestions[0].starts_at == base


def test_fatigue_aware_scoring_prefers_lower_fatigue_window() -> None:
    base = datetime(2026, 4, 20, 9, 0, tzinfo=timezone.utc)
    due_at = base + timedelta(hours=8)
    task = build_task(task_id="deep-work", due_at=due_at, estimated_minutes=60, priority=4, energy_required=5)
    events = [
        build_external_event(event_id="midday-busy", starts_at=base + timedelta(hours=1), ends_at=base + timedelta(hours=4)),
        build_external_event(event_id="late-busy", starts_at=base + timedelta(hours=5), ends_at=base + timedelta(hours=8)),
    ]
    patterns = [
        FatiguePatternModel(
            id="pattern-morning",
            user_id="user-1",
            weekday=0,
            time_bucket=FatigueTimeBucket.MORNING,
            avg_fatigue=4.5,
            min_fatigue=4.0,
            max_fatigue=5.0,
            fatigue_variance=0.1,
            sample_count=4,
            confidence=0.8,
            trend_direction=FatigueTrendDirection.STABLE,
            last_signal_at=base - timedelta(days=1),
            last_computed_at=base - timedelta(hours=1),
            metadata_json={},
        ),
        FatiguePatternModel(
            id="pattern-afternoon",
            user_id="user-1",
            weekday=0,
            time_bucket=FatigueTimeBucket.AFTERNOON,
            avg_fatigue=1.0,
            min_fatigue=1.0,
            max_fatigue=1.5,
            fatigue_variance=0.1,
            sample_count=4,
            confidence=0.8,
            trend_direction=FatigueTrendDirection.STABLE,
            last_signal_at=base - timedelta(days=1),
            last_computed_at=base - timedelta(hours=1),
            metadata_json={},
        ),
    ]
    service, _, _, _ = build_service(tasks=[task], events=events, patterns=patterns)

    suggestions = service.suggest_blocks(
        user_id="user-1",
        payload=InternalCalendarSuggestRequest(
            task_ids=["deep-work"],
            window_start=base,
            window_end=due_at,
            max_suggestions=1,
        ),
    )

    assert len(suggestions) == 1
    assert suggestions[0].starts_at == base + timedelta(hours=4)


def test_deadline_watcher_detects_under_allocated_near_deadline_task() -> None:
    now = datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc)
    due_at = now + timedelta(hours=10)
    task = build_task(task_id="task-1", due_at=due_at, estimated_minutes=120, priority=5)
    existing = build_block(
        block_id="allocated",
        starts_at=now + timedelta(hours=1),
        ends_at=now + timedelta(hours=1, minutes=30),
        task_id="task-1",
    )
    service, calendar_repo, _, task_repo = build_service(tasks=[task], blocks=[existing])
    watcher = DeadlineWatcher(service)

    results = watcher.run(user_id="user-1", now=now, due_within=timedelta(hours=24))

    assert len(results) == 1
    assert results[0].task_id == "task-1"
    assert results[0].action == "urgent_suggestion_created"
    assert len(calendar_repo.created_blocks) == 1
    assert task_repo.logged_events[0]["event_type"] == "deadline_risk_detected"


def test_deadline_watcher_does_not_flag_completed_task() -> None:
    now = datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc)
    done_task = build_task(
        task_id="done-task",
        due_at=now + timedelta(hours=10),
        estimated_minutes=60,
        status=TaskStatus.DONE,
    )
    service, calendar_repo, _, task_repo = build_service(tasks=[done_task])
    watcher = DeadlineWatcher(service)

    results = watcher.run(user_id="user-1", now=now, due_within=timedelta(hours=24))

    assert results == []
    assert calendar_repo.created_blocks == []
    assert task_repo.logged_events == []


def test_deadline_watcher_avoids_duplicate_urgent_block_creation() -> None:
    now = datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc)
    due_at = now + timedelta(hours=10)
    task = build_task(task_id="task-1", due_at=due_at, estimated_minutes=120, priority=5)
    existing_urgent = build_block(
        block_id="existing-urgent",
        starts_at=now + timedelta(hours=2),
        ends_at=now + timedelta(hours=3),
        task_id="task-1",
        status=CalendarBlockStatus.SUGGESTED,
    )
    service, calendar_repo, _, task_repo = build_service(tasks=[task], blocks=[existing_urgent])
    watcher = DeadlineWatcher(service)

    results = watcher.run(user_id="user-1", now=now, due_within=timedelta(hours=24))

    assert len(results) == 1
    assert results[0].action == "logged_only"
    assert calendar_repo.created_blocks == []
    assert task_repo.logged_events[0]["payload"]["action"] == "logged_only"


def test_owner_scoping_remains_correct_for_scheduling_reads() -> None:
    base = datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc)
    my_task = build_task(task_id="mine", user_id="user-1", due_at=base + timedelta(hours=6))
    other_block = build_block(
        block_id="other-block",
        starts_at=base,
        ends_at=base + timedelta(hours=1),
        user_id="user-2",
        task_id="other",
    )
    other_event = build_external_event(
        event_id="other-event",
        starts_at=base + timedelta(hours=1),
        ends_at=base + timedelta(hours=2),
        user_id="user-2",
    )
    users = [build_user(user_id="user-1"), build_user(user_id="user-2")]
    preferences = [build_preferences(user_id="user-1"), build_preferences(user_id="user-2")]
    service, calendar_repo, external_repo, _ = build_service(
        tasks=[my_task],
        blocks=[other_block],
        events=[other_event],
        users=users,
        preferences=preferences,
    )

    suggestions = service.suggest_blocks(
        user_id="user-1",
        payload=InternalCalendarSuggestRequest(
            task_ids=["mine"],
            window_start=base,
            window_end=base + timedelta(hours=4),
            max_suggestions=1,
        ),
    )

    assert len(suggestions) == 1
    assert suggestions[0].task_id == "mine"
    assert calendar_repo.window_calls == ["user-1"]
    assert external_repo.calls == ["user-1"]
