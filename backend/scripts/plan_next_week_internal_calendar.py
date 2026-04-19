from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.db import connect_db, get_database_url
from app.models.internal_calendar import CalendarBlockStatus, CalendarBlockType
from app.models.memory import LearnedMemoryModel
from app.models.task import TaskModel
from app.repositories.connectors import ConnectorRepository
from app.repositories.internal_calendar import InternalCalendarRepository
from app.repositories.memories import MemoryRepository
from app.repositories.tasks import TaskRepository
from app.repositories.users import UserRepository
from app.services.internal_calendar_service import InternalCalendarService, _Interval, _bucket_for_datetime


@dataclass(slots=True)
class PlanningHints:
    selected_memories: list[LearnedMemoryModel]
    statements: list[str]
    bucket_bias: dict[str, float]
    avoid_evening: bool = False
    prefer_morning: bool = False
    prefer_shorter_blocks: bool = False
    shorter_block_cap_minutes: int | None = None


@dataclass(slots=True)
class TaskSlice:
    task: TaskModel
    slice_index: int
    total_slices: int
    duration_minutes: int


@dataclass(slots=True)
class PlannedBlock:
    task_id: str
    title: str
    starts_at: datetime
    ends_at: datetime
    score: float
    reason_summary: str
    memory_statements: list[str]
    block_type: CalendarBlockType
    priority_snapshot: int
    energy_snapshot: int | None
    slice_index: int
    total_slices: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan next week's task blocks and add them to internal_calendar."
    )
    parser.add_argument("--user-id", required=True, help="Target user id")
    parser.add_argument("--max-blocks", type=int, default=16, help="Maximum blocks to create")
    parser.add_argument("--task-limit", type=int, default=50, help="Maximum open tasks to consider")
    parser.add_argument("--memory-limit", type=int, default=12, help="Maximum learned memories to inspect")
    parser.add_argument("--min-planned-blocks", type=int, default=2, help="Do not write anything unless at least this many blocks are planned")
    parser.add_argument(
        "--start-date",
        help="Override start date in YYYY-MM-DD. Defaults to next Monday in the user's timezone.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan without writing internal_calendar rows",
    )
    parser.add_argument(
        "--sync-to-google",
        action="store_true",
        help="Create blocks with sync_to_google=true",
    )
    return parser.parse_args()


def next_monday(local_today: date) -> date:
    days_until_monday = (7 - local_today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    return local_today + timedelta(days=days_until_monday)


def build_next_week_window(*, timezone_name: str, start_date_override: str | None) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone_name)
    if start_date_override:
        local_start_date = date.fromisoformat(start_date_override)
    else:
        local_start_date = next_monday(datetime.now(zone).date())
    local_start = datetime.combine(local_start_date, time.min, tzinfo=zone)
    local_end = local_start + timedelta(days=7)
    return local_start.astimezone(UTC), local_end.astimezone(UTC)


def memory_signal(memory: LearnedMemoryModel) -> tuple[str | None, float]:
    statement = memory.statement.casefold()
    confidence_weight = max(0.2, float(memory.confidence))
    bucket = memory.metadata_json.get("time_bucket")
    if isinstance(bucket, str):
        bucket = bucket.casefold()

    if "better energy in the" in statement:
        return bucket, confidence_weight
    if "accepts morning focus blocks" in statement:
        return "morning", confidence_weight * 1.2
    if "better execution window than evening" in statement:
        return "morning", confidence_weight
    if "avoids demanding evening work" in statement:
        return "evening", -confidence_weight * 1.2
    if "move focus sessions out of the evening" in statement:
        return "evening", -confidence_weight * 1.3
    if "weaker execution window" in statement:
        return bucket or "evening", -confidence_weight
    if "high fatigue in the" in statement:
        return bucket, -confidence_weight
    return bucket, 0.0


def load_planning_hints(*, memory_repository: MemoryRepository, user_id: str, limit: int) -> PlanningHints:
    planning_query = (
        "Plan next week's work using fatigue patterns, accepted schedule behavior, "
        "timing preferences, and learned planning constraints"
    )
    memories = memory_repository.get_relevant_memories(
        user_id=user_id,
        query=planning_query,
        domain="planning",
        limit=limit,
        embedding=None,
    )

    bucket_bias: dict[str, float] = defaultdict(float)
    shorter_block_cap_minutes: int | None = None
    for memory in memories:
        bucket, score = memory_signal(memory)
        if bucket:
            bucket_bias[bucket] += score
        value = memory.metadata_json.get("preferred_duration_minutes")
        if isinstance(value, int) and value > 0:
            shorter_block_cap_minutes = value if shorter_block_cap_minutes is None else min(shorter_block_cap_minutes, value)

    filtered_memories: list[LearnedMemoryModel] = []
    for memory in memories:
        bucket = memory.metadata_json.get("time_bucket")
        bucket_key = bucket.casefold() if isinstance(bucket, str) else None
        statement = memory.statement.casefold()
        contradictory = False
        if bucket_key and bucket_bias.get(bucket_key):
            if bucket_bias[bucket_key] >= 0.35 and "high fatigue in the" in statement:
                contradictory = True
            if bucket_bias[bucket_key] <= -0.35 and "better energy in the" in statement:
                contradictory = True
        if contradictory:
            continue
        filtered_memories.append(memory)

    selected_memories = filtered_memories[:limit]
    statements = [memory.statement for memory in selected_memories]

    return PlanningHints(
        selected_memories=selected_memories,
        statements=statements,
        bucket_bias=dict(bucket_bias),
        avoid_evening=(bucket_bias.get("evening", 0.0) + bucket_bias.get("night", 0.0)) < -0.3,
        prefer_morning=bucket_bias.get("morning", 0.0) > 0.3,
        prefer_shorter_blocks=shorter_block_cap_minutes is not None or any(
            "prefers shorter" in memory.statement.casefold() for memory in selected_memories
        ),
        shorter_block_cap_minutes=shorter_block_cap_minutes,
    )


def sort_tasks(tasks: list[TaskModel]) -> list[TaskModel]:
    return sorted(
        tasks,
        key=lambda task: (
            task.due_at or datetime.max.replace(tzinfo=UTC),
            -task.priority,
            -(task.energy_required or 0),
            task.created_at or datetime.min.replace(tzinfo=UTC),
            task.id,
        ),
    )


def resolve_block_type(task: TaskModel) -> CalendarBlockType:
    if (task.energy_required or 0) >= 4 or task.priority >= 4:
        return CalendarBlockType.FOCUS_BLOCK
    return CalendarBlockType.SUGGESTED_TASK


def resolve_session_minutes(*, task: TaskModel, hints: PlanningHints) -> int:
    estimated = task.estimated_minutes or 60
    if (task.energy_required or 0) >= 4:
        session = 60
    elif task.priority >= 4:
        session = 50
    else:
        session = 45

    if hints.prefer_shorter_blocks and hints.shorter_block_cap_minutes:
        session = min(session, hints.shorter_block_cap_minutes)
    elif hints.prefer_shorter_blocks:
        session = min(session, 45)

    if estimated <= 30:
        session = min(session, 30)
    return max(25, session)


def build_task_slices(*, tasks: list[TaskModel], hints: PlanningHints, max_blocks: int) -> list[TaskSlice]:
    slices: list[TaskSlice] = []
    for task in tasks:
        estimated = max(task.estimated_minutes or 60, 25)
        session_minutes = resolve_session_minutes(task=task, hints=hints)
        session_count = max(1, math.ceil(estimated / session_minutes))
        if task.priority <= 2:
            session_count = min(session_count, 2)
        elif task.priority == 3:
            session_count = min(session_count, 3)
        else:
            session_count = min(session_count, 4)

        remaining = estimated
        task_slices: list[TaskSlice] = []
        for index in range(session_count):
            duration = session_minutes if index < session_count - 1 else max(25, min(session_minutes, remaining))
            task_slices.append(
                TaskSlice(
                    task=task,
                    slice_index=index + 1,
                    total_slices=session_count,
                    duration_minutes=duration,
                )
            )
            remaining = max(0, remaining - duration)

        slices.extend(task_slices)
        if len(slices) >= max_blocks:
            break

    return slices[:max_blocks]


def weekday_key(*, value: datetime, timezone_name: str) -> str:
    local_day = value.astimezone(ZoneInfo(timezone_name)).date()
    return local_day.isoformat()


def is_weekday_slot(*, value: datetime, timezone_name: str) -> bool:
    return value.astimezone(ZoneInfo(timezone_name)).weekday() < 5


def task_has_existing_block(
    *,
    repository: InternalCalendarRepository,
    user_id: str,
    task_id: str,
    window_start: datetime,
    window_end: datetime,
) -> bool:
    existing = repository.list_task_blocks_in_window(
        user_id=user_id,
        task_id=task_id,
        window_start=window_start,
        window_end=window_end,
    )
    return bool(existing)


def preferred_bucket_for_task(task: TaskModel) -> str:
    if (task.energy_required or 0) >= 4 or task.priority >= 4:
        return "morning"
    if (task.energy_required or 0) <= 2 and task.priority <= 3:
        return "afternoon"
    return "morning"


def apply_memory_adjustments(
    *,
    task_slice: TaskSlice,
    scored_slots: list,
    hints: PlanningHints,
    timezone_name: str,
    day_loads: dict[str, int],
    task_day_assignments: dict[str, set[str]],
) -> list[tuple[float, object]]:
    adjusted: list[tuple[float, object]] = []
    preferred_bucket = preferred_bucket_for_task(task_slice.task)
    zone = ZoneInfo(timezone_name)
    task_id = task_slice.task.id

    for scored in scored_slots:
        local_start = scored.slot.starts_at.astimezone(zone)
        bucket = _bucket_for_datetime(local_start).value
        score = float(scored.score)
        day_key = local_start.date().isoformat()
        current_day_load = day_loads.get(day_key, 0)
        same_task_days = task_day_assignments.get(task_id, set())

        score -= current_day_load * 1.1
        if day_key in same_task_days:
            score -= 0.9
        else:
            score += 0.4

        if preferred_bucket == "morning" and bucket == "morning":
            score += 1.6
        elif preferred_bucket == "afternoon" and bucket == "afternoon":
            score += 1.0
        elif preferred_bucket == "afternoon" and bucket == "morning":
            score -= 0.25

        score += hints.bucket_bias.get(bucket, 0.0) * 1.4

        if hints.prefer_morning and bucket == "morning":
            score += 0.6
        if hints.avoid_evening and bucket in {"evening", "night"}:
            score -= 3.5

        if task_slice.task.due_at is not None:
            hours_until_due = (task_slice.task.due_at - scored.slot.ends_at).total_seconds() / 3600
            if hours_until_due < 0:
                score -= 20.0
            elif hours_until_due < 12:
                score += 1.3
            elif hours_until_due < 48:
                score += 0.7

        if not is_weekday_slot(value=scored.slot.starts_at, timezone_name=timezone_name):
            score -= 6.0

        adjusted.append((round(score, 4), scored))

    adjusted.sort(
        key=lambda item: (
            -item[0],
            day_loads.get(weekday_key(value=item[1].slot.starts_at, timezone_name=timezone_name), 0),
            item[1].slot.starts_at,
            item[1].slot.ends_at,
        )
    )
    return adjusted


def build_reason_summary(
    *,
    task_slice: TaskSlice,
    base_score: float,
    memory_statements: list[str],
    timezone_name: str,
    starts_at: datetime,
) -> str:
    local_start = starts_at.astimezone(ZoneInfo(timezone_name))
    bucket = _bucket_for_datetime(local_start).value
    session_note = f"session {task_slice.slice_index}/{task_slice.total_slices}"
    due_clause = ""
    if task_slice.task.due_at is not None:
        due_clause = f", scheduled before due date {task_slice.task.due_at.date().isoformat()}"
    memory_clause = ""
    if memory_statements:
        memory_clause = f", aligned with: {', '.join(memory_statements[:2])}"
    return (
        f"Next-week planner selected a {bucket} weekday slot for {session_note} "
        f"with score {round(base_score, 2)}{due_clause}{memory_clause}"
    )


def choose_weekday_scored_slots(*, adjusted_slots: list[tuple[float, object]], timezone_name: str) -> list[tuple[float, object]]:
    weekday_slots = [
        item for item in adjusted_slots
        if is_weekday_slot(value=item[1].slot.starts_at, timezone_name=timezone_name)
    ]
    return weekday_slots or adjusted_slots


def build_plan(
    *,
    user_id: str,
    window_start: datetime,
    window_end: datetime,
    max_blocks: int,
    task_limit: int,
    memory_limit: int,
) -> tuple[list[PlannedBlock], PlanningHints]:
    database_url = get_database_url()
    with connect_db(database_url=database_url) as connection:
        user_repository = UserRepository(connection)
        task_repository = TaskRepository(connection)
        calendar_repository = InternalCalendarRepository(connection)
        connector_repository = ConnectorRepository(connection)
        memory_repository = MemoryRepository(connection)
        user = user_repository.get_user(user_id)
        if user is None:
            raise RuntimeError(f"User {user_id} not found")

        preferences = user_repository.get_preferences(user_id)
        hints = load_planning_hints(memory_repository=memory_repository, user_id=user_id, limit=memory_limit)
        service = InternalCalendarService(
            connection,
            repository=calendar_repository,
            task_repository=task_repository,
            connector_repository=connector_repository,
            user_repository=user_repository,
        )

        tasks = sort_tasks(
            task_repository.list_schedulable_tasks(
                user_id=user_id,
                task_ids=None,
                limit=task_limit,
            )
        )
        tasks = [
            task for task in tasks
            if not task_has_existing_block(
                repository=calendar_repository,
                user_id=user_id,
                task_id=task.id,
                window_start=window_start,
                window_end=window_end,
            )
        ]

        task_slices = build_task_slices(tasks=tasks, hints=hints, max_blocks=max_blocks)
        internal_blocks = calendar_repository.list_blocks_in_window(
            user_id=user_id,
            window_start=window_start,
            window_end=window_end,
        )
        external_events = connector_repository.list_external_calendar_events(
            user_id=user_id,
            start=window_start,
            end=window_end,
        )
        busy_intervals = service.build_busy_intervals(
            external_events=external_events,
            internal_blocks=internal_blocks,
        )

        planned: list[PlannedBlock] = []
        day_loads: dict[str, int] = defaultdict(int)
        task_day_assignments: dict[str, set[str]] = defaultdict(set)

        for existing_block in internal_blocks:
            day_loads[weekday_key(value=existing_block.starts_at, timezone_name=user.timezone)] += 1
            if existing_block.task_id:
                task_day_assignments[existing_block.task_id].add(
                    weekday_key(value=existing_block.starts_at, timezone_name=user.timezone)
                )

        for task_slice in task_slices:
            free_windows = service.get_candidate_free_windows(
                user_id=user_id,
                window_start=window_start,
                window_end=window_end,
                duration=timedelta(minutes=task_slice.duration_minutes),
                busy_intervals=busy_intervals,
                user=user,
                preferences=preferences,
            )
            if not free_windows:
                continue

            scored_slots = service._score_candidate_windows(task=task_slice.task, free_windows=free_windows, user=user)
            if not scored_slots:
                continue

            adjusted_slots = apply_memory_adjustments(
                task_slice=task_slice,
                scored_slots=scored_slots,
                hints=hints,
                timezone_name=user.timezone,
                day_loads=day_loads,
                task_day_assignments=task_day_assignments,
            )
            ranked_slots = choose_weekday_scored_slots(
                adjusted_slots=adjusted_slots,
                timezone_name=user.timezone,
            )
            if not ranked_slots:
                continue

            final_score, selected = ranked_slots[0]
            local_day_key = weekday_key(value=selected.slot.starts_at, timezone_name=user.timezone)
            memory_statements = hints.statements[:3]
            reason_summary = build_reason_summary(
                task_slice=task_slice,
                base_score=final_score,
                memory_statements=memory_statements,
                timezone_name=user.timezone,
                starts_at=selected.slot.starts_at,
            )

            planned.append(
                PlannedBlock(
                    task_id=task_slice.task.id,
                    title=task_slice.task.title,
                    starts_at=selected.slot.starts_at,
                    ends_at=selected.slot.ends_at,
                    score=final_score,
                    reason_summary=reason_summary,
                    memory_statements=memory_statements,
                    block_type=resolve_block_type(task_slice.task),
                    priority_snapshot=task_slice.task.priority,
                    energy_snapshot=task_slice.task.energy_required,
                    slice_index=task_slice.slice_index,
                    total_slices=task_slice.total_slices,
                )
            )
            day_loads[local_day_key] += 1
            task_day_assignments[task_slice.task.id].add(local_day_key)
            busy_intervals = service._merge_intervals(
                [*busy_intervals, _Interval(selected.slot.starts_at, selected.slot.ends_at)]
            )

        return planned, hints


def persist_plan(
    *,
    user_id: str,
    planned: list[PlannedBlock],
    window_start: datetime,
    window_end: datetime,
    sync_to_google: bool,
) -> None:
    database_url = get_database_url()
    with connect_db(database_url=database_url) as connection:
        calendar_repository = InternalCalendarRepository(connection)
        for item in planned:
            created = calendar_repository.create_block(
                user_id=user_id,
                task_id=item.task_id,
                title=f"Focus - {item.title}" if item.total_slices == 1 else f"Focus - {item.title} ({item.slice_index}/{item.total_slices})",
                block_type=item.block_type,
                starts_at=item.starts_at,
                ends_at=item.ends_at,
                status=CalendarBlockStatus.SUGGESTED,
                sync_to_google=sync_to_google,
                source="next_week_planner_script",
                reason_summary=item.reason_summary,
                priority_snapshot=item.priority_snapshot,
                energy_snapshot=item.energy_snapshot,
                metadata_json={
                    "generated_from": "plan_next_week_internal_calendar",
                    "window_score": round(item.score, 3),
                    "memory_statements": item.memory_statements,
                    "planning_window_start": window_start.isoformat(),
                    "planning_window_end": window_end.isoformat(),
                    "task_slice_index": item.slice_index,
                    "task_slice_total": item.total_slices,
                },
            )
            calendar_repository.log_calendar_event(
                user_id=user_id,
                event_type="calendar_block_suggested",
                block_id=created.id,
                payload={
                    "task_id": item.task_id,
                    "starts_at": item.starts_at.isoformat(),
                    "ends_at": item.ends_at.isoformat(),
                    "source": "next_week_planner_script",
                    "slice_index": item.slice_index,
                    "slice_total": item.total_slices,
                },
            )


def main() -> int:
    args = parse_args()
    database_url = get_database_url()

    with connect_db(database_url=database_url) as connection:
        user_repository = UserRepository(connection)
        user = user_repository.get_user(args.user_id)
        if user is None:
            raise RuntimeError(f"User {args.user_id} not found")
        window_start, window_end = build_next_week_window(
            timezone_name=user.timezone,
            start_date_override=args.start_date,
        )

    planned, hints = build_plan(
        user_id=args.user_id,
        window_start=window_start,
        window_end=window_end,
        max_blocks=args.max_blocks,
        task_limit=args.task_limit,
        memory_limit=args.memory_limit,
    )

    print(
        f"Planning window: {window_start.isoformat()} -> {window_end.isoformat()} "
        f"for user {args.user_id}"
    )
    print(f"Learned planning memories used: {len(hints.statements)}")
    for statement in hints.statements[:5]:
        print(f"  - {statement}")

    if len(planned) < args.min_planned_blocks:
        print(
            f"\nPlanned only {len(planned)} blocks, below min threshold {args.min_planned_blocks}. "
            "Nothing was written."
        )
        return 0

    if args.dry_run:
        print(f"\nPlanned {len(planned)} blocks (dry run).")
    else:
        persist_plan(
            user_id=args.user_id,
            planned=planned,
            window_start=window_start,
            window_end=window_end,
            sync_to_google=args.sync_to_google,
        )
        print(f"\nCreated {len(planned)} next-week internal calendar blocks.")

    for item in planned:
        print(
            "  - "
            f"{item.title} [{item.slice_index}/{item.total_slices}] ({item.task_id}) | "
            f"{item.starts_at.isoformat()} -> {item.ends_at.isoformat()} | "
            f"score={item.score}"
        )
        print(f"    reason: {item.reason_summary}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
