from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import psycopg
from fastapi import HTTPException, status

from app.models.internal_calendar import CalendarBlockStatus, CalendarBlockType, FeedbackResponseType
from app.models.task import TaskModel, TaskStatus
from app.repositories.internal_calendar import InternalCalendarRepository
from app.repositories.tasks import TaskRepository
from app.schemas.internal_calendar import (
    CalendarFeedbackRead,
    InternalCalendarBlockRead,
    InternalCalendarCompleteRequest,
    InternalCalendarConfirmRequest,
    InternalCalendarListFilters,
    InternalCalendarRejectRequest,
    InternalCalendarRescheduleRequest,
    InternalCalendarSuggestRequest,
)
from app.schemas.task import CompleteTaskRequest, TaskRead


@dataclass(slots=True)
class _ScheduledSlot:
    starts_at: datetime
    ends_at: datetime


class InternalCalendarService:
    def __init__(self, connection: psycopg.Connection) -> None:
        self.repository = InternalCalendarRepository(connection)
        self.task_repository = TaskRepository(connection)

    def suggest_blocks(
        self,
        *,
        user_id: str,
        payload: InternalCalendarSuggestRequest,
    ) -> list[InternalCalendarBlockRead]:
        tasks = self.task_repository.list_schedulable_tasks(
            user_id=user_id,
            task_ids=payload.task_ids,
            limit=payload.max_suggestions * 5,
        )
        occupied = self.repository.list_blocks_in_window(
            user_id=user_id,
            window_start=payload.window_start,
            window_end=payload.window_end,
        )

        suggestions: list[InternalCalendarBlockRead] = []
        occupied_intervals = sorted((block.starts_at, block.ends_at) for block in occupied)

        for task in self._sort_tasks_for_scheduling(tasks):
            if len(suggestions) >= payload.max_suggestions:
                break

            duration = timedelta(minutes=self._resolve_duration_minutes(task))
            slot = self._find_slot(
                occupied_intervals=occupied_intervals,
                window_start=payload.window_start,
                window_end=payload.window_end,
                duration=duration,
            )
            if slot is None:
                continue

            created = self.repository.create_block(
                user_id=user_id,
                task_id=task.id,
                title=f"Focus - {task.title}",
                block_type=CalendarBlockType.SUGGESTED_TASK,
                starts_at=slot.starts_at,
                ends_at=slot.ends_at,
                status=CalendarBlockStatus.SUGGESTED,
                sync_to_google=payload.sync_to_google_default,
                source="system",
                reason_summary=self._build_reason_summary(task),
                priority_snapshot=task.priority,
                energy_snapshot=task.energy_required,
                metadata_json={"generated_from": "task_suggestion_mvp"},
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
            occupied_intervals.append((created.starts_at, created.ends_at))
            occupied_intervals.sort(key=lambda interval: (interval[0], interval[1]))
            suggestions.append(InternalCalendarBlockRead.from_model(created))

        return suggestions

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
        self._require_block(block_id=block_id, user_id=user_id)
        values = {
            "status": CalendarBlockStatus.CONFIRMED,
            "confirmed_at": datetime.now(timezone.utc),
        }
        if payload.sync_to_google is not None:
            values["sync_to_google"] = payload.sync_to_google

        block = self.repository.update_block(block_id=block_id, user_id=user_id, values=values)
        assert block is not None
        self.repository.insert_feedback(
            block_id=block_id,
            user_id=user_id,
            response_type=FeedbackResponseType.ACCEPTED,
            reason_text=payload.reason_text,
            fatigue_score=payload.fatigue_score,
        )
        self.repository.log_calendar_event(
            user_id=user_id,
            event_type="calendar_block_confirmed",
            block_id=block.id,
            payload={"status": block.status.value, "sync_to_google": block.sync_to_google},
        )
        return InternalCalendarBlockRead.from_model(block)

    def reject_block(
        self,
        *,
        user_id: str,
        block_id: str,
        payload: InternalCalendarRejectRequest,
    ) -> InternalCalendarBlockRead:
        self._require_block(block_id=block_id, user_id=user_id)
        block = self.repository.update_block(
            block_id=block_id,
            user_id=user_id,
            values={
                "status": CalendarBlockStatus.REJECTED,
                "rejected_at": datetime.now(timezone.utc),
            },
        )
        assert block is not None
        self.repository.insert_feedback(
            block_id=block_id,
            user_id=user_id,
            response_type=FeedbackResponseType.REJECTED,
            reason_code=payload.reason_code,
            reason_text=payload.reason_text,
            fatigue_score=payload.fatigue_score,
        )
        self.repository.log_calendar_event(
            user_id=user_id,
            event_type="calendar_block_rejected",
            block_id=block.id,
            payload={"reason_code": payload.reason_code},
        )
        return InternalCalendarBlockRead.from_model(block)

    def reschedule_block(
        self,
        *,
        user_id: str,
        block_id: str,
        payload: InternalCalendarRescheduleRequest,
    ) -> InternalCalendarBlockRead:
        block = self._require_block(block_id=block_id, user_id=user_id)

        if payload.auto_find_new_slot:
            duration = block.ends_at - block.starts_at
            search_start = max(block.ends_at, datetime.now(timezone.utc))
            search_end = search_start + timedelta(days=14)
            occupied = self.repository.list_blocks_in_window(
                user_id=user_id,
                window_start=search_start,
                window_end=search_end,
                exclude_block_id=block_id,
            )
            slot = self._find_slot(
                occupied_intervals=sorted((item.starts_at, item.ends_at) for item in occupied),
                window_start=search_start,
                window_end=search_end,
                duration=duration,
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
        self.repository.insert_feedback(
            block_id=block_id,
            user_id=user_id,
            response_type=FeedbackResponseType.MOVED,
            reason_code=payload.reason_code,
            reason_text=payload.reason_text,
            fatigue_score=payload.fatigue_score,
        )
        self.repository.log_calendar_event(
            user_id=user_id,
            event_type="calendar_block_rescheduled",
            block_id=updated.id,
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
        self.repository.insert_feedback(
            block_id=block_id,
            user_id=user_id,
            response_type=FeedbackResponseType.COMPLETED,
            reason_text=payload.notes,
        )
        self.repository.log_calendar_event(
            user_id=user_id,
            event_type="calendar_block_completed",
            block_id=completed.id,
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

    def _require_block(self, *, block_id: str, user_id: str):
        block = self.repository.get_block(block_id=block_id, user_id=user_id)
        if block is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar block not found")
        return block

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

    def _build_reason_summary(self, task: TaskModel) -> str:
        if task.due_at is not None:
            return f"Scheduled early against due date {task.due_at.date().isoformat()} with priority {task.priority}"
        return f"Scheduled from open task queue with priority {task.priority}"

    def _find_slot(
        self,
        *,
        occupied_intervals: list[tuple[datetime, datetime]],
        window_start: datetime,
        window_end: datetime,
        duration: timedelta,
    ) -> _ScheduledSlot | None:
        cursor = window_start

        for interval_start, interval_end in sorted(occupied_intervals, key=lambda interval: (interval[0], interval[1])):
            if interval_end <= cursor:
                continue
            if cursor + duration <= interval_start:
                return _ScheduledSlot(starts_at=cursor, ends_at=cursor + duration)
            if interval_start < window_end:
                cursor = max(cursor, interval_end)
            if cursor + duration > window_end:
                return None

        if cursor + duration <= window_end:
            return _ScheduledSlot(starts_at=cursor, ends_at=cursor + duration)
        return None

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
