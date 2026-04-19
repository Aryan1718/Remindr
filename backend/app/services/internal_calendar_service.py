from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import psycopg
from fastapi import HTTPException, status

from app.models.external_calendar_event import ExternalCalendarEventModel
from app.models.fatigue import FatigueTimeBucket
from app.models.internal_calendar import (
    CalendarBlockStatus,
    CalendarBlockType,
    CalendarFeedbackModel,
    FeedbackResponseType,
    InternalCalendarBlockModel,
)
from app.models.task import TaskModel
from app.models.user import UserModel, UserPreferencesModel
from app.repositories.connectors import ConnectorRepository
from app.repositories.fatigue import FatigueRepository
from app.repositories.internal_calendar import InternalCalendarRepository
from app.repositories.tasks import TaskRepository
from app.repositories.users import UserRepository
from app.schemas.internal_calendar import (
    CalendarFeedbackRead,
    InternalCalendarBlockRead,
    InternalCalendarCompleteRequest,
    InternalCalendarConfirmRequest,
    InternalCalendarFeedbackCreateRequest,
    InternalCalendarListFilters,
    InternalCalendarRejectRequest,
    InternalCalendarRescheduleRequest,
    InternalCalendarSuggestRequest,
)
from app.schemas.task import CompleteTaskRequest, TaskRead
from app.services.notification_service import NotificationService
from app.workers.rq import enqueue_memory_distillation


@dataclass(slots=True)
class _Interval:
    starts_at: datetime
    ends_at: datetime

    @property
    def duration(self) -> timedelta:
        return self.ends_at - self.starts_at


@dataclass(slots=True)
class _ScoredSlot:
    slot: _Interval
    score: float
    lateness_penalty: float
    fit_score: float
    fatigue_score: float
    priority_score: float
    deadline_score: float


def _resolve_timezone(name: str | None) -> ZoneInfo:
    candidate = name or "UTC"
    try:
        return ZoneInfo(candidate)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _bucket_for_datetime(value: datetime) -> FatigueTimeBucket:
    hour = value.hour
    if 5 <= hour <= 11:
        return FatigueTimeBucket.MORNING
    if 12 <= hour <= 16:
        return FatigueTimeBucket.AFTERNOON
    if 17 <= hour <= 20:
        return FatigueTimeBucket.EVENING
    return FatigueTimeBucket.NIGHT


class InternalCalendarService:
    def __init__(
        self,
        connection: psycopg.Connection | None = None,
        *,
        repository: InternalCalendarRepository | None = None,
        task_repository: TaskRepository | None = None,
        fatigue_repository: FatigueRepository | None = None,
        connector_repository: ConnectorRepository | None = None,
        user_repository: UserRepository | None = None,
    ) -> None:
        self.connection = connection
        self.repository = repository or self._require_repo(InternalCalendarRepository, connection)
        self.task_repository = task_repository or self._require_repo(TaskRepository, connection)
        self.fatigue_repository = fatigue_repository or self._require_repo(FatigueRepository, connection)
        self.connector_repository = connector_repository or self._require_repo(ConnectorRepository, connection)
        self.user_repository = user_repository or self._require_repo(UserRepository, connection)
        self.enqueue_memory_distillation = enqueue_memory_distillation

    def suggest_blocks(
        self,
        *,
        user_id: str,
        payload: InternalCalendarSuggestRequest,
    ) -> list[InternalCalendarBlockRead]:
        user = self.user_repository.get_user(user_id)
        preferences = self.user_repository.get_preferences(user_id)
        tasks = self.task_repository.list_schedulable_tasks(
            user_id=user_id,
            task_ids=payload.task_ids,
            limit=payload.max_suggestions * 5,
        )
        internal_blocks = self.repository.list_blocks_in_window(
            user_id=user_id,
            window_start=payload.window_start,
            window_end=payload.window_end,
        )
        external_events = self._list_external_calendar_events(
            user_id=user_id,
            start=payload.window_start,
            end=payload.window_end,
        )

        suggestions: list[InternalCalendarBlockRead] = []
        busy_intervals = self.build_busy_intervals(
            external_events=external_events,
            internal_blocks=internal_blocks,
        )

        for task in self._sort_tasks_for_scheduling(tasks):
            if len(suggestions) >= payload.max_suggestions:
                break

            duration = timedelta(minutes=self._resolve_duration_minutes(task))
            free_windows = self.get_candidate_free_windows(
                user_id=user_id,
                window_start=payload.window_start,
                window_end=payload.window_end,
                duration=duration,
                busy_intervals=busy_intervals,
                user=user,
                preferences=preferences,
            )
            scored_slot = self._select_best_slot(
                task=task,
                free_windows=free_windows,
                user=user,
            )
            if scored_slot is None:
                continue

            created = self.repository.create_block(
                user_id=user_id,
                task_id=task.id,
                title=f"Focus - {task.title}",
                block_type=CalendarBlockType.SUGGESTED_TASK,
                starts_at=scored_slot.slot.starts_at,
                ends_at=scored_slot.slot.ends_at,
                status=CalendarBlockStatus.SUGGESTED,
                sync_to_google=payload.sync_to_google_default,
                source="system",
                reason_summary=self._build_reason_summary(task, scored_slot=scored_slot),
                priority_snapshot=task.priority,
                energy_snapshot=task.energy_required,
                metadata_json={
                    "generated_from": "task_suggestion_scheduler",
                    "window_score": round(scored_slot.score, 3),
                },
            )
            self.repository.log_calendar_event(
                user_id=user_id,
                event_type="calendar_block_suggested",
                block_id=created.id,
                payload={
                    "task_id": task.id,
                    "starts_at": created.starts_at.isoformat(),
                    "ends_at": created.ends_at.isoformat(),
                },
            )
            busy_intervals = self._merge_intervals([*busy_intervals, _Interval(created.starts_at, created.ends_at)])
            suggestions.append(InternalCalendarBlockRead.from_model(created))

        return suggestions

    def get_candidate_free_windows(
        self,
        *,
        user_id: str,
        window_start: datetime,
        window_end: datetime,
        duration: timedelta | None = None,
        busy_intervals: list[_Interval] | None = None,
        user: UserModel | None = None,
        preferences: UserPreferencesModel | None = None,
    ) -> list[_Interval]:
        if user is None:
            user = self.user_repository.get_user(user_id)
        if preferences is None:
            preferences = self.user_repository.get_preferences(user_id)

        effective_busy = busy_intervals
        if effective_busy is None:
            internal_blocks = self.repository.list_blocks_in_window(
                user_id=user_id,
                window_start=window_start,
                window_end=window_end,
            )
            external_events = self._list_external_calendar_events(
                user_id=user_id,
                start=window_start,
                end=window_end,
            )
            effective_busy = self.build_busy_intervals(
                external_events=external_events,
                internal_blocks=internal_blocks,
            )

        return self._subtract_busy_from_allowed_windows(
            window_start=window_start,
            window_end=window_end,
            busy_intervals=effective_busy,
            duration=duration,
            timezone_name=(user.timezone if user is not None else None),
            preferences=preferences,
        )

    def list_blocks(
        self,
        *,
        user_id: str,
        filters: InternalCalendarListFilters,
    ) -> list[InternalCalendarBlockRead]:
        blocks = self.repository.list_blocks(
            user_id=user_id,
            start=filters.start,
            end=filters.end,
            status=filters.status,
            task_id=filters.task_id,
            limit=filters.limit,
        )
        return [InternalCalendarBlockRead.from_model(block) for block in blocks]

    def get_block_detail(self, *, user_id: str, block_id: str) -> tuple[InternalCalendarBlockRead, list[CalendarFeedbackRead]]:
        block = self.repository.get_block(block_id=block_id, user_id=user_id)
        if block is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar block not found")

        feedback = self.repository.list_feedback_for_block(block_id=block_id, user_id=user_id)
        return (
            InternalCalendarBlockRead.from_model(block),
            [CalendarFeedbackRead.from_model(item) for item in feedback],
        )

    def confirm_block(
        self,
        *,
        user_id: str,
        block_id: str,
        payload: InternalCalendarConfirmRequest,
    ) -> InternalCalendarBlockRead:
        block = self._require_block(block_id=block_id, user_id=user_id)
        if block.status == CalendarBlockStatus.CONFIRMED:
            if payload.sync_to_google is not None and payload.sync_to_google != block.sync_to_google:
                updated = self.repository.update_block(
                    block_id=block_id,
                    user_id=user_id,
                    values={"sync_to_google": payload.sync_to_google},
                )
                assert updated is not None
                return InternalCalendarBlockRead.from_model(updated)
            return InternalCalendarBlockRead.from_model(block)
        self._ensure_transition_allowed(
            block=block,
            allowed_statuses={CalendarBlockStatus.SUGGESTED, CalendarBlockStatus.RESCHEDULED},
            action="confirm",
        )
        values = {
            "status": CalendarBlockStatus.CONFIRMED,
            "confirmed_at": datetime.now(timezone.utc),
        }
        if payload.sync_to_google is not None:
            values["sync_to_google"] = payload.sync_to_google

        updated = self.repository.update_block(block_id=block_id, user_id=user_id, values=values)
        assert updated is not None
        self._record_feedback_and_event(
            block_id=block_id,
            user_id=user_id,
            response_type=FeedbackResponseType.ACCEPTED,
            trigger_source="calendar_confirm",
            reason_text=payload.reason_text,
            fatigue_score=payload.fatigue_score,
            event_type="suggestion_accepted",
            payload={"status": updated.status.value, "sync_to_google": updated.sync_to_google},
        )
        return InternalCalendarBlockRead.from_model(updated)

    def reject_block(
        self,
        *,
        user_id: str,
        block_id: str,
        payload: InternalCalendarRejectRequest,
    ) -> InternalCalendarBlockRead:
        block = self._require_block(block_id=block_id, user_id=user_id)
        if block.status == CalendarBlockStatus.REJECTED:
            return InternalCalendarBlockRead.from_model(block)
        self._ensure_transition_allowed(
            block=block,
            allowed_statuses={CalendarBlockStatus.SUGGESTED, CalendarBlockStatus.RESCHEDULED, CalendarBlockStatus.CONFIRMED},
            action="reject",
        )
        updated = self.repository.update_block(
            block_id=block_id,
            user_id=user_id,
            values={
                "status": CalendarBlockStatus.REJECTED,
                "rejected_at": datetime.now(timezone.utc),
            },
        )
        assert updated is not None
        self._record_feedback_and_event(
            block_id=block_id,
            user_id=user_id,
            response_type=FeedbackResponseType.REJECTED,
            trigger_source="calendar_reject",
            reason_code=payload.reason_code,
            reason_text=payload.reason_text,
            fatigue_score=payload.fatigue_score,
            event_type="suggestion_rejected",
            payload={"reason_code": payload.reason_code, "status": updated.status.value},
        )
        return InternalCalendarBlockRead.from_model(updated)

    def reschedule_block(
        self,
        *,
        user_id: str,
        block_id: str,
        payload: InternalCalendarRescheduleRequest,
    ) -> InternalCalendarBlockRead:
        block = self._require_block(block_id=block_id, user_id=user_id)
        self._ensure_transition_allowed(
            block=block,
            allowed_statuses={CalendarBlockStatus.SUGGESTED, CalendarBlockStatus.RESCHEDULED, CalendarBlockStatus.CONFIRMED},
            action="reschedule",
        )

        if payload.auto_find_new_slot:
            duration = block.ends_at - block.starts_at
            search_start = max(block.ends_at, datetime.now(timezone.utc))
            search_end = search_start + timedelta(days=14)
            user = self.user_repository.get_user(user_id)
            preferences = self.user_repository.get_preferences(user_id)
            occupied = self.repository.list_blocks_in_window(
                user_id=user_id,
                window_start=search_start,
                window_end=search_end,
                exclude_block_id=block_id,
            )
            external_events = self._list_external_calendar_events(
                user_id=user_id,
                start=search_start,
                end=search_end,
            )
            slot = self._select_earliest_slot(
                free_windows=self.get_candidate_free_windows(
                    user_id=user_id,
                    window_start=search_start,
                    window_end=search_end,
                    duration=duration,
                    busy_intervals=self.build_busy_intervals(
                        external_events=external_events,
                        internal_blocks=occupied,
                    ),
                    user=user,
                    preferences=preferences,
                ),
                window_start=search_start,
            )
            if slot is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No available reschedule slot found in the next 14 days",
                )
            new_starts_at = slot.starts_at
            new_ends_at = slot.ends_at
        else:
            assert payload.new_starts_at is not None
            assert payload.new_ends_at is not None
            self._ensure_no_overlap(
                user_id=user_id,
                starts_at=payload.new_starts_at,
                ends_at=payload.new_ends_at,
                exclude_block_id=block_id,
            )
            new_starts_at = payload.new_starts_at
            new_ends_at = payload.new_ends_at

        updated = self.repository.update_block(
            block_id=block_id,
            user_id=user_id,
            values={
                "starts_at": new_starts_at,
                "ends_at": new_ends_at,
                "status": CalendarBlockStatus.RESCHEDULED,
                "reschedule_count": block.reschedule_count + 1,
            },
        )
        assert updated is not None
        self._record_feedback_and_event(
            block_id=block_id,
            user_id=user_id,
            response_type=FeedbackResponseType.MOVED,
            trigger_source="calendar_reschedule",
            reason_code=payload.reason_code,
            reason_text=payload.reason_text,
            fatigue_score=payload.fatigue_score,
            event_type="suggestion_rescheduled",
            payload={
                "starts_at": updated.starts_at.isoformat(),
                "ends_at": updated.ends_at.isoformat(),
                "reschedule_count": updated.reschedule_count,
            },
        )
        return InternalCalendarBlockRead.from_model(updated)

    def complete_block(
        self,
        *,
        user_id: str,
        block_id: str,
        payload: InternalCalendarCompleteRequest,
    ) -> tuple[InternalCalendarBlockRead, TaskRead | None]:
        block = self._require_block(block_id=block_id, user_id=user_id)
        if block.status == CalendarBlockStatus.DONE:
            return InternalCalendarBlockRead.from_model(block), None
        self._ensure_transition_allowed(
            block=block,
            allowed_statuses={
                CalendarBlockStatus.SUGGESTED,
                CalendarBlockStatus.RESCHEDULED,
                CalendarBlockStatus.CONFIRMED,
            },
            action="complete",
        )
        completed = self.repository.update_block(
            block_id=block_id,
            user_id=user_id,
            values={
                "status": CalendarBlockStatus.DONE,
                "completed_at": datetime.now(timezone.utc),
                "metadata_json": {
                    **block.metadata_json,
                    **({"completion_notes": payload.notes} if payload.notes else {}),
                },
            },
        )
        assert completed is not None
        self._record_feedback_and_event(
            block_id=block_id,
            user_id=user_id,
            response_type=FeedbackResponseType.COMPLETED,
            trigger_source="calendar_feedback",
            reason_text=payload.notes,
            event_type="suggestion_completed",
            payload={"task_completed": payload.task_completed},
        )

        completed_task: TaskRead | None = None
        if payload.task_completed and block.task_id is not None:
            task = self.task_repository.complete_task(
                task_id=block.task_id,
                user_id=user_id,
                payload=CompleteTaskRequest(completed_at=datetime.now(timezone.utc)),
            )
            if task is not None:
                completed_task = TaskRead.from_model(task)

        return InternalCalendarBlockRead.from_model(completed), completed_task

    def create_feedback(
        self,
        *,
        user_id: str,
        block_id: str,
        payload: InternalCalendarFeedbackCreateRequest,
    ) -> CalendarFeedbackRead:
        self._require_block(block_id=block_id, user_id=user_id)
        feedback = self._record_feedback_and_event(
            block_id=block_id,
            user_id=user_id,
            response_type=payload.response_type,
            trigger_source="calendar_feedback",
            reason_code=payload.reason_code,
            reason_text=payload.reason_text,
            fatigue_score=payload.fatigue_score,
            event_type=self._feedback_event_type(payload.response_type),
            payload={"response_type": payload.response_type.value},
        )
        return CalendarFeedbackRead.from_model(feedback)

    def queue_block_reminder(self, *, user_id: str, block_id: str) -> tuple[object, object | None]:
        block = self._require_block(block_id=block_id, user_id=user_id)
        user = self.user_repository.get_user(user_id)
        notification_service = NotificationService(self.connection)
        return notification_service.queue_internal_calendar_suggestion_reminder(
            block=block,
            timezone_name=(user.timezone if user is not None else None),
        )

    def _require_block(self, *, block_id: str, user_id: str):
        block = self.repository.get_block(block_id=block_id, user_id=user_id)
        if block is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar block not found")
        return block

    def _ensure_transition_allowed(
        self,
        *,
        block: InternalCalendarBlockModel,
        allowed_statuses: set[CalendarBlockStatus],
        action: str,
    ) -> None:
        if block.status not in allowed_statuses:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot {action} a calendar block in {block.status.value} status",
            )

    def _record_feedback_and_event(
        self,
        *,
        block_id: str,
        user_id: str,
        response_type: FeedbackResponseType,
        trigger_source: str,
        event_type: str,
        payload: dict[str, object],
        reason_code: str | None = None,
        reason_text: str | None = None,
        fatigue_score: int | None = None,
    ) -> CalendarFeedbackModel:
        feedback = self.repository.insert_feedback(
            block_id=block_id,
            user_id=user_id,
            response_type=response_type,
            reason_code=reason_code,
            reason_text=reason_text,
            fatigue_score=fatigue_score,
        )
        self.repository.log_calendar_event(
            user_id=user_id,
            event_type=event_type,
            block_id=block_id,
            payload={
                **payload,
                "response_type": response_type.value,
                **({"reason_code": reason_code} if reason_code is not None else {}),
                **({"fatigue_score": fatigue_score} if fatigue_score is not None else {}),
            },
        )
        self.enqueue_memory_distillation(
            user_id=user_id,
            trigger_source=trigger_source,
            entity_type="calendar_feedback",
            entity_id=feedback.id,
        )
        return feedback

    def _feedback_event_type(self, response_type: FeedbackResponseType) -> str:
        return {
            FeedbackResponseType.ACCEPTED: "suggestion_accepted",
            FeedbackResponseType.REJECTED: "suggestion_rejected",
            FeedbackResponseType.MOVED: "suggestion_rescheduled",
            FeedbackResponseType.COMPLETED: "suggestion_completed",
            FeedbackResponseType.SNOOZED: "suggestion_snoozed",
            FeedbackResponseType.IGNORED: "suggestion_ignored",
        }[response_type]

    def build_busy_intervals(
        self,
        *,
        external_events: list[ExternalCalendarEventModel],
        internal_blocks: list,
    ) -> list[_Interval]:
        intervals = [
            _Interval(starts_at=event.starts_at, ends_at=event.ends_at)
            for event in external_events
            if event.starts_at < event.ends_at
        ]
        intervals.extend(
            _Interval(starts_at=block.starts_at, ends_at=block.ends_at)
            for block in internal_blocks
            if block.starts_at < block.ends_at
            and block.status
            in {
                CalendarBlockStatus.SUGGESTED,
                CalendarBlockStatus.CONFIRMED,
                CalendarBlockStatus.RESCHEDULED,
            }
        )
        return self._merge_intervals(intervals)

    def _list_external_calendar_events(
        self,
        *,
        user_id: str,
        start: datetime,
        end: datetime,
    ) -> list[ExternalCalendarEventModel]:
        connector_repository = getattr(self, "connector_repository", None)
        if connector_repository is None:
            return []
        return connector_repository.list_external_calendar_events(
            user_id=user_id,
            start=start,
            end=end,
        )

    def _sort_tasks_for_scheduling(self, tasks: list[TaskModel]) -> list[TaskModel]:
        return sorted(
            tasks,
            key=lambda task: (
                task.due_at or datetime.max.replace(tzinfo=timezone.utc),
                -task.priority,
                task.created_at or datetime.min.replace(tzinfo=timezone.utc),
                task.id,
            ),
        )

    def _resolve_duration_minutes(self, task: TaskModel) -> int:
        if task.estimated_minutes is None or task.estimated_minutes <= 0:
            return 60
        return task.estimated_minutes

    def _build_reason_summary(self, task: TaskModel, *, scored_slot: _ScoredSlot | None = None) -> str:
        if scored_slot is not None and task.due_at is not None:
            return (
                f"Placed before due date {task.due_at.date().isoformat()} "
                f"with score {round(scored_slot.score, 2)} and priority {task.priority}"
            )
        if task.due_at is not None:
            return f"Scheduled early against due date {task.due_at.date().isoformat()} with priority {task.priority}"
        return f"Scheduled from open task queue with priority {task.priority}"

    def _select_best_slot(
        self,
        *,
        task: TaskModel,
        free_windows: list[_Interval],
        user: UserModel | None,
    ) -> _ScoredSlot | None:
        candidates = self._score_candidate_windows(task=task, free_windows=free_windows, user=user)
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda item: (
                item.score,
                -item.slot.starts_at.timestamp(),
                -item.slot.ends_at.timestamp(),
            ),
        )

    def _select_earliest_slot(
        self,
        *,
        free_windows: list[_Interval],
        window_start: datetime,
    ) -> _Interval | None:
        for free_window in sorted(free_windows, key=lambda item: (item.starts_at, item.ends_at)):
            if free_window.ends_at > window_start:
                return free_window
        return None

    def _score_candidate_windows(
        self,
        *,
        task: TaskModel,
        free_windows: list[_Interval],
        user: UserModel | None,
    ) -> list[_ScoredSlot]:
        scored: list[_ScoredSlot] = []
        duration = timedelta(minutes=self._resolve_duration_minutes(task))
        for window in free_windows:
            if window.duration < duration:
                continue

            slot = _Interval(starts_at=window.starts_at, ends_at=window.starts_at + duration)
            fit_score = self._duration_fit_score(window=window, duration=duration)
            deadline_score = self._deadline_window_score(task=task, slot=slot)
            priority_score = float(task.priority) * 0.8
            fatigue_score = self._fatigue_compatibility_score(task=task, slot=slot, timezone_name=user.timezone if user else None)
            lateness_penalty = self._lateness_penalty(task=task, slot=slot)
            total = deadline_score + priority_score + fit_score + fatigue_score - lateness_penalty
            scored.append(
                _ScoredSlot(
                    slot=slot,
                    score=round(total, 4),
                    lateness_penalty=round(lateness_penalty, 4),
                    fit_score=round(fit_score, 4),
                    fatigue_score=round(fatigue_score, 4),
                    priority_score=round(priority_score, 4),
                    deadline_score=round(deadline_score, 4),
                )
            )

        return sorted(scored, key=lambda item: (-item.score, item.slot.starts_at, item.slot.ends_at))

    def _duration_fit_score(self, *, window: _Interval, duration: timedelta) -> float:
        window_minutes = max(window.duration.total_seconds() / 60, 1)
        duration_minutes = max(duration.total_seconds() / 60, 1)
        overflow_ratio = max((window_minutes - duration_minutes) / duration_minutes, 0.0)
        return max(0.0, 4.0 - min(overflow_ratio, 3.0))

    def _deadline_window_score(self, *, task: TaskModel, slot: _Interval) -> float:
        if task.due_at is None:
            return 0.5
        minutes_until_due = max((task.due_at - slot.ends_at).total_seconds() / 60, 0.0)
        if minutes_until_due <= 360:
            return 8.0
        if minutes_until_due <= 1440:
            return 6.0
        if minutes_until_due <= 4320:
            return 3.5
        return 1.0

    def _lateness_penalty(self, *, task: TaskModel, slot: _Interval) -> float:
        penalty = 0.0
        local_slot = slot.starts_at.astimezone(slot.starts_at.tzinfo or timezone.utc)
        if local_slot.hour >= 22 or local_slot.hour < 6:
            penalty += 4.0
        elif local_slot.hour >= 21:
            penalty += 1.5
        if task.due_at is not None and slot.ends_at > task.due_at:
            penalty += 20.0
        if slot.duration < timedelta(minutes=20):
            penalty += 1.0
        return penalty

    def _fatigue_compatibility_score(self, *, task: TaskModel, slot: _Interval, timezone_name: str | None) -> float:
        if task.energy_required is None:
            return 0.0

        local_dt = slot.starts_at.astimezone(_resolve_timezone(timezone_name))
        pattern = self.fatigue_repository.get_pattern(
            user_id=task.user_id,
            weekday=local_dt.weekday(),
            time_bucket=_bucket_for_datetime(local_dt),
        )
        if pattern is None:
            return 0.0

        available_energy = max(0.0, 5.0 - float(pattern.avg_fatigue))
        mismatch = abs(float(task.energy_required) - available_energy)
        return max(-2.5, 3.0 - mismatch)

    def _subtract_busy_from_allowed_windows(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
        busy_intervals: list[_Interval],
        duration: timedelta | None,
        timezone_name: str | None,
        preferences: UserPreferencesModel | None,
    ) -> list[_Interval]:
        allowed_windows = self._build_allowed_windows(
            window_start=window_start,
            window_end=window_end,
            timezone_name=timezone_name,
            preferences=preferences,
        )
        free: list[_Interval] = []

        for allowed in allowed_windows:
            cursor = allowed.starts_at
            for busy in busy_intervals:
                if busy.ends_at <= allowed.starts_at:
                    continue
                if busy.starts_at >= allowed.ends_at:
                    break
                clipped_start = max(busy.starts_at, allowed.starts_at)
                clipped_end = min(busy.ends_at, allowed.ends_at)
                if cursor < clipped_start:
                    candidate = _Interval(cursor, clipped_start)
                    if duration is None or candidate.duration >= duration:
                        free.append(candidate)
                cursor = max(cursor, clipped_end)
            if cursor < allowed.ends_at:
                candidate = _Interval(cursor, allowed.ends_at)
                if duration is None or candidate.duration >= duration:
                    free.append(candidate)

        return [item for item in free if item.starts_at < item.ends_at]

    def _build_allowed_windows(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
        timezone_name: str | None,
        preferences: UserPreferencesModel | None,
    ) -> list[_Interval]:
        if preferences is None or preferences.work_start_time is None or preferences.work_end_time is None:
            return [_Interval(window_start, window_end)]

        zone = _resolve_timezone(timezone_name)
        local_start = window_start.astimezone(zone)
        local_end = window_end.astimezone(zone)
        start_time = time.fromisoformat(str(preferences.work_start_time))
        end_time = time.fromisoformat(str(preferences.work_end_time))
        work_days = set(preferences.work_days or [1, 2, 3, 4, 5])
        windows: list[_Interval] = []

        cursor_day = local_start.date()
        while cursor_day <= local_end.date():
            weekday = cursor_day.isoweekday()
            if weekday in work_days:
                day_start = datetime.combine(cursor_day, start_time, tzinfo=zone)
                day_end = datetime.combine(cursor_day, end_time, tzinfo=zone)
                if day_end > day_start:
                    clipped_start = max(day_start, local_start)
                    clipped_end = min(day_end, local_end)
                    if clipped_start < clipped_end:
                        windows.append(
                            _Interval(
                                starts_at=clipped_start.astimezone(window_start.tzinfo or timezone.utc),
                                ends_at=clipped_end.astimezone(window_start.tzinfo or timezone.utc),
                            )
                        )
            cursor_day += timedelta(days=1)

        return windows

    def _merge_intervals(self, intervals: list[_Interval]) -> list[_Interval]:
        merged: list[_Interval] = []
        for interval in sorted(intervals, key=lambda item: (item.starts_at, item.ends_at)):
            if interval.starts_at >= interval.ends_at:
                continue
            if not merged or interval.starts_at > merged[-1].ends_at:
                merged.append(_Interval(interval.starts_at, interval.ends_at))
                continue
            merged[-1].ends_at = max(merged[-1].ends_at, interval.ends_at)
        return merged

    def _require_repo(self, repo_cls, connection: psycopg.Connection | None):
        if connection is None:
            raise RuntimeError(f"{repo_cls.__name__} requires a database connection")
        return repo_cls(connection)

    def _ensure_no_overlap(
        self,
        *,
        user_id: str,
        starts_at: datetime,
        ends_at: datetime,
        exclude_block_id: str | None = None,
    ) -> None:
        overlapping = self.repository.list_blocks_in_window(
            user_id=user_id,
            window_start=starts_at,
            window_end=ends_at,
            exclude_block_id=exclude_block_id,
        )
        if overlapping:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Calendar block overlaps an existing internal calendar block",
            )
        external_events = self._list_external_calendar_events(
            user_id=user_id,
            start=starts_at,
            end=ends_at,
        )
        if external_events:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Calendar block overlaps an external calendar event",
            )
