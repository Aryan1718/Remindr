from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from fastapi import HTTPException
from pydantic import ValidationError

from app.models.internal_calendar import (
    CalendarBlockStatus,
    CalendarBlockType,
    CalendarFeedbackModel,
    FeedbackResponseType,
    InternalCalendarBlockModel,
)
from app.services.internal_calendar_service import InternalCalendarService
from app.schemas.internal_calendar import (
    InternalCalendarCompleteRequest,
    InternalCalendarConfirmRequest,
    InternalCalendarRejectRequest,
    InternalCalendarRescheduleRequest,
)


def _block(
    *,
    block_id: str = "block-1",
    user_id: str = "user-1",
    task_id: str | None = "task-1",
    status: CalendarBlockStatus = CalendarBlockStatus.SUGGESTED,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    reschedule_count: int = 0,
    sync_to_google: bool = False,
    metadata_json: dict | None = None,
) -> InternalCalendarBlockModel:
    starts = starts_at or datetime(2026, 4, 18, 9, 0, tzinfo=timezone.utc)
    ends = ends_at or (starts + timedelta(hours=1))
    return InternalCalendarBlockModel(
        id=block_id,
        user_id=user_id,
        task_id=task_id,
        title="Focus - Test",
        block_type=CalendarBlockType.SUGGESTED_TASK,
        starts_at=starts,
        ends_at=ends,
        status=status,
        sync_to_google=sync_to_google,
        external_event_id=None,
        source="system",
        reason_summary="Test reason",
        reschedule_count=reschedule_count,
        priority_snapshot=3,
        energy_snapshot=2,
        metadata_json=metadata_json or {},
        created_at=starts - timedelta(hours=1),
        updated_at=starts - timedelta(minutes=30),
        confirmed_at=None,
        rejected_at=None,
        completed_at=None,
    )


def _feedback(response_type: FeedbackResponseType) -> CalendarFeedbackModel:
    return CalendarFeedbackModel(
        id="feedback-1",
        calendar_block_id="block-1",
        user_id="user-1",
        response_type=response_type,
        reason_code=None,
        reason_text=None,
        fatigue_score=None,
        created_at=datetime.now(timezone.utc),
    )


class InternalCalendarServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = InternalCalendarService.__new__(InternalCalendarService)
        self.service.repository = MagicMock()
        self.service.task_repository = MagicMock()

    def test_confirm_block_updates_status_and_writes_feedback(self) -> None:
        original = _block()
        updated = _block(status=CalendarBlockStatus.CONFIRMED, sync_to_google=True)
        self.service.repository.get_block.return_value = original
        self.service.repository.update_block.return_value = updated
        self.service.repository.insert_feedback.return_value = _feedback(FeedbackResponseType.ACCEPTED)

        result = self.service.confirm_block(
            user_id="user-1",
            block_id="block-1",
            payload=InternalCalendarConfirmRequest(sync_to_google=True, fatigue_score=2, reason_text="Works"),
        )

        self.assertEqual(result.status, CalendarBlockStatus.CONFIRMED)
        self.service.repository.update_block.assert_called_once()
        self.service.repository.insert_feedback.assert_called_once_with(
            block_id="block-1",
            user_id="user-1",
            response_type=FeedbackResponseType.ACCEPTED,
            reason_code=None,
            reason_text="Works",
            fatigue_score=2,
        )
        self.service.repository.log_calendar_event.assert_called_once()

    def test_reject_block_writes_reason_and_fatigue(self) -> None:
        original = _block()
        updated = _block(status=CalendarBlockStatus.REJECTED)
        self.service.repository.get_block.return_value = original
        self.service.repository.update_block.return_value = updated
        self.service.repository.insert_feedback.return_value = _feedback(FeedbackResponseType.REJECTED)

        result = self.service.reject_block(
            user_id="user-1",
            block_id="block-1",
            payload=InternalCalendarRejectRequest(
                reason_code="too_tired",
                reason_text="Need a break",
                fatigue_score=5,
            ),
        )

        self.assertEqual(result.status, CalendarBlockStatus.REJECTED)
        self.service.repository.insert_feedback.assert_called_once_with(
            block_id="block-1",
            user_id="user-1",
            response_type=FeedbackResponseType.REJECTED,
            reason_code="too_tired",
            reason_text="Need a break",
            fatigue_score=5,
        )

    def test_reschedule_block_updates_time_status_count_and_feedback(self) -> None:
        start = datetime(2026, 4, 18, 9, 0, tzinfo=timezone.utc)
        end = start + timedelta(hours=1)
        new_start = start + timedelta(hours=2)
        new_end = end + timedelta(hours=2)
        original = _block(starts_at=start, ends_at=end, status=CalendarBlockStatus.CONFIRMED, reschedule_count=1)
        updated = _block(
            starts_at=new_start,
            ends_at=new_end,
            status=CalendarBlockStatus.RESCHEDULED,
            reschedule_count=2,
        )
        self.service.repository.get_block.return_value = original
        self.service.repository.update_block.return_value = updated
        self.service.repository.insert_feedback.return_value = _feedback(FeedbackResponseType.MOVED)
        self.service.repository.list_blocks_in_window.return_value = []

        result = self.service.reschedule_block(
            user_id="user-1",
            block_id="block-1",
            payload=InternalCalendarRescheduleRequest(
                new_starts_at=new_start,
                new_ends_at=new_end,
                reason_text="Afternoon is better",
            ),
        )

        self.assertEqual(result.status, CalendarBlockStatus.RESCHEDULED)
        self.assertEqual(result.reschedule_count, 2)
        self.service.repository.insert_feedback.assert_called_once_with(
            block_id="block-1",
            user_id="user-1",
            response_type=FeedbackResponseType.MOVED,
            reason_code=None,
            reason_text="Afternoon is better",
            fatigue_score=None,
        )

    def test_complete_block_marks_done_and_writes_feedback(self) -> None:
        original = _block(status=CalendarBlockStatus.CONFIRMED)
        updated = _block(status=CalendarBlockStatus.DONE, metadata_json={"completion_notes": "Finished"})
        self.service.repository.get_block.return_value = original
        self.service.repository.update_block.return_value = updated
        self.service.repository.insert_feedback.return_value = _feedback(FeedbackResponseType.COMPLETED)

        block, task = self.service.complete_block(
            user_id="user-1",
            block_id="block-1",
            payload=InternalCalendarCompleteRequest(notes="Finished"),
        )

        self.assertEqual(block.status, CalendarBlockStatus.DONE)
        self.assertIsNone(task)
        self.service.repository.insert_feedback.assert_called_once_with(
            block_id="block-1",
            user_id="user-1",
            response_type=FeedbackResponseType.COMPLETED,
            reason_code=None,
            reason_text="Finished",
            fatigue_score=None,
        )

    def test_other_user_cannot_mutate_block(self) -> None:
        self.service.repository.get_block.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            self.service.confirm_block(
                user_id="user-2",
                block_id="block-1",
                payload=InternalCalendarConfirmRequest(),
            )

        self.assertEqual(ctx.exception.status_code, 404)
        self.service.repository.update_block.assert_not_called()
        self.service.repository.insert_feedback.assert_not_called()

    def test_invalid_fatigue_score_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            InternalCalendarRejectRequest(reason_text="too much", fatigue_score=6)

    def test_duplicate_complete_is_idempotent(self) -> None:
        done_block = _block(status=CalendarBlockStatus.DONE)
        self.service.repository.get_block.return_value = done_block

        block, task = self.service.complete_block(
            user_id="user-1",
            block_id="block-1",
            payload=InternalCalendarCompleteRequest(notes="ignored retry"),
        )

        self.assertEqual(block.status, CalendarBlockStatus.DONE)
        self.assertIsNone(task)
        self.service.repository.update_block.assert_not_called()
        self.service.repository.insert_feedback.assert_not_called()

    def test_invalid_transition_returns_conflict(self) -> None:
        rejected_block = _block(status=CalendarBlockStatus.REJECTED)
        self.service.repository.get_block.return_value = rejected_block

        with self.assertRaises(HTTPException) as ctx:
            self.service.confirm_block(
                user_id="user-1",
                block_id="block-1",
                payload=InternalCalendarConfirmRequest(),
            )

        self.assertEqual(ctx.exception.status_code, 409)
        self.service.repository.update_block.assert_not_called()
        self.service.repository.insert_feedback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
