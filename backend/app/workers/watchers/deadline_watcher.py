from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.models.internal_calendar import CalendarBlockStatus
from app.models.task import TaskModel, TaskStatus
from app.schemas.internal_calendar import InternalCalendarSuggestRequest
from app.services.internal_calendar_service import InternalCalendarService


@dataclass(slots=True)
class DeadlineWatcherResult:
    task_id: str
    user_id: str
    allocated_minutes: int
    estimated_minutes: int
    free_minutes_before_deadline: int
    action: str


class DeadlineWatcher:
    def __init__(self, scheduling_service: InternalCalendarService) -> None:
        self.scheduling_service = scheduling_service
        self.task_repository = scheduling_service.task_repository
        self.calendar_repository = scheduling_service.repository
        self.user_repository = scheduling_service.user_repository

    def run(
        self,
        *,
        user_id: str | None = None,
        due_within: timedelta = timedelta(days=3),
        limit: int = 200,
        now: datetime | None = None,
    ) -> list[DeadlineWatcherResult]:
        effective_now = now or datetime.now(timezone.utc)
        due_before = effective_now + due_within
        tasks = self.task_repository.list_deadline_watch_candidates(
            user_id=user_id,
            due_before=due_before,
            limit=limit,
        )

        results: list[DeadlineWatcherResult] = []
        for task in tasks:
            outcome = self._evaluate_task(task=task, now=effective_now)
            if outcome is not None:
                results.append(outcome)
        return results

    def _evaluate_task(self, *, task: TaskModel, now: datetime) -> DeadlineWatcherResult | None:
        if task.status in {TaskStatus.DONE, TaskStatus.ARCHIVED, TaskStatus.SKIPPED}:
            return None
        if task.due_at is None or task.due_at <= now:
            return None
        if task.estimated_minutes is None or task.estimated_minutes <= 0:
            return None

        allocated_blocks = self.calendar_repository.list_task_blocks_in_window(
            user_id=task.user_id,
            task_id=task.id,
            window_start=now,
            window_end=task.due_at,
        )
        allocated_minutes = self._sum_allocated_minutes(allocated_blocks)
        remaining_needed = max(task.estimated_minutes - allocated_minutes, 0)
        if remaining_needed <= 0:
            return None

        user = self.user_repository.get_user(task.user_id)
        preferences = self.user_repository.get_preferences(task.user_id)
        free_windows = self.scheduling_service.get_candidate_free_windows(
            user_id=task.user_id,
            window_start=now,
            window_end=task.due_at,
            user=user,
            preferences=preferences,
        )
        free_minutes = int(sum(window.duration.total_seconds() / 60 for window in free_windows))
        if not self._is_deadline_risky(task=task, now=now, remaining_needed=remaining_needed, free_minutes=free_minutes):
            return None

        action = "logged_only"
        if not self._has_existing_urgent_candidate(blocks=allocated_blocks, now=now):
            suggestions = self.scheduling_service.suggest_blocks(
                user_id=task.user_id,
                payload=InternalCalendarSuggestRequest(
                    task_ids=[task.id],
                    window_start=now,
                    window_end=task.due_at,
                    max_suggestions=1,
                    sync_to_google_default=False,
                ),
            )
            if suggestions:
                action = "urgent_suggestion_created"

        self.task_repository.log_task_event(
            user_id=task.user_id,
            event_type="deadline_risk_detected",
            task_id=task.id,
            payload={
                "due_at": task.due_at.isoformat(),
                "estimated_minutes": task.estimated_minutes,
                "allocated_minutes": allocated_minutes,
                "remaining_needed_minutes": remaining_needed,
                "free_minutes_before_deadline": free_minutes,
                "action": action,
            },
        )
        return DeadlineWatcherResult(
            task_id=task.id,
            user_id=task.user_id,
            allocated_minutes=allocated_minutes,
            estimated_minutes=task.estimated_minutes,
            free_minutes_before_deadline=free_minutes,
            action=action,
        )

    def _is_deadline_risky(
        self,
        *,
        task: TaskModel,
        now: datetime,
        remaining_needed: int,
        free_minutes: int,
    ) -> bool:
        assert task.due_at is not None
        hours_until_due = max((task.due_at - now).total_seconds() / 3600, 0.0)
        if free_minutes < remaining_needed:
            return True
        if hours_until_due <= 24 and remaining_needed >= 30:
            return True
        if hours_until_due <= 48 and remaining_needed >= 60 and free_minutes <= int(remaining_needed * 1.5):
            return True
        return False

    def _has_existing_urgent_candidate(self, *, blocks, now: datetime) -> bool:
        for block in blocks:
            if block.starts_at < now:
                continue
            if block.status != CalendarBlockStatus.SUGGESTED:
                continue
            return True
        return False

    def _sum_allocated_minutes(self, blocks) -> int:
        total = 0
        for block in blocks:
            if block.status in {
                CalendarBlockStatus.SUGGESTED,
                CalendarBlockStatus.CONFIRMED,
                CalendarBlockStatus.RESCHEDULED,
                CalendarBlockStatus.DONE,
            }:
                total += int((block.ends_at - block.starts_at).total_seconds() / 60)
        return total
