from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.models.task import TaskModel, TaskStatus
from app.schemas.task import CompleteTaskRequest
from app.services.task_service import TaskService


def _task(*, task_id: str = "task-1", user_id: str = "user-1", status: TaskStatus = TaskStatus.PENDING) -> TaskModel:
    now = datetime(2026, 4, 19, 18, 0, tzinfo=timezone.utc)
    return TaskModel(
        id=task_id,
        user_id=user_id,
        title="Test task",
        description=None,
        priority=3,
        estimated_minutes=30,
        actual_minutes=None,
        energy_required=2,
        due_at=None,
        status=status,
        source="user",
        metadata_json={},
        created_at=now,
        updated_at=now,
        completed_at=now if status == TaskStatus.DONE else None,
    )


class TaskServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = TaskService.__new__(TaskService)
        self.service.repository = MagicMock()
        self.service.enqueue_memory_distillation = MagicMock()

    def test_complete_task_enqueues_memory_distillation_on_real_transition(self) -> None:
        existing = _task(status=TaskStatus.PENDING)
        completed = _task(status=TaskStatus.DONE)
        self.service.repository.get_task.return_value = existing
        self.service.repository.complete_task.return_value = completed

        result = self.service.complete_task(
            user_id="user-1",
            task_id="task-1",
            payload=CompleteTaskRequest(actual_minutes=25),
        )

        self.assertEqual(result.status, TaskStatus.DONE)
        self.service.repository.log_task_event.assert_called_once_with(
            user_id="user-1",
            event_type="task_completed",
            task_id="task-1",
            payload={"actual_minutes": 25},
        )
        self.service.enqueue_memory_distillation.assert_called_once_with(
            user_id="user-1",
            trigger_source="task_complete",
            entity_type="task",
            entity_id="task-1",
        )

    def test_complete_task_is_idempotent_for_already_done_task(self) -> None:
        done_task = _task(status=TaskStatus.DONE)
        self.service.repository.get_task.return_value = done_task

        result = self.service.complete_task(
            user_id="user-1",
            task_id="task-1",
            payload=CompleteTaskRequest(),
        )

        self.assertEqual(result.status, TaskStatus.DONE)
        self.service.repository.complete_task.assert_not_called()
        self.service.repository.log_task_event.assert_not_called()
        self.service.enqueue_memory_distillation.assert_not_called()

    def test_complete_task_raises_not_found_without_enqueue(self) -> None:
        self.service.repository.get_task.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            self.service.complete_task(
                user_id="user-1",
                task_id="missing",
                payload=CompleteTaskRequest(),
            )

        self.assertEqual(ctx.exception.status_code, 404)
        self.service.repository.complete_task.assert_not_called()
        self.service.enqueue_memory_distillation.assert_not_called()


if __name__ == "__main__":
    unittest.main()
