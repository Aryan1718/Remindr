from __future__ import annotations

import psycopg
from fastapi import HTTPException, status

from app.repositories.tasks import TaskRepository
from app.models.task import TaskStatus
from app.schemas.task import CompleteTaskRequest, TaskCreateRequest, TaskFilters, TaskRead, TaskUpdateRequest
from app.services.notification_service import NotificationService
from app.workers.rq import enqueue_memory_distillation


class TaskService:
    def __init__(self, connection: psycopg.Connection) -> None:
        self.repository = TaskRepository(connection)
        self.enqueue_memory_distillation = enqueue_memory_distillation

    def create_task(self, *, user_id: str, payload: TaskCreateRequest) -> TaskRead:
        task = self.repository.create_task(user_id=user_id, payload=payload)
        self.repository.log_task_event(
            user_id=user_id,
            event_type="task_created",
            task_id=task.id,
            payload={"status": task.status.value, "source": task.source},
        )
        return TaskRead.from_model(task)

    def list_tasks(self, *, user_id: str, filters: TaskFilters) -> list[TaskRead]:
        tasks = self.repository.list_tasks(user_id=user_id, filters=filters)
        return [TaskRead.from_model(task) for task in tasks]

    def get_task(self, *, user_id: str, task_id: str) -> TaskRead:
        task = self.repository.get_task(task_id=task_id, user_id=user_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return TaskRead.from_model(task)

    def update_task(self, *, user_id: str, task_id: str, payload: TaskUpdateRequest) -> TaskRead:
        task = self.repository.update_task(task_id=task_id, user_id=user_id, payload=payload)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        self.repository.log_task_event(
            user_id=user_id,
            event_type="task_updated",
            task_id=task.id,
            payload={"updated_fields": sorted(payload.model_fields_set)},
        )
        return TaskRead.from_model(task)

    def complete_task(self, *, user_id: str, task_id: str, payload: CompleteTaskRequest) -> TaskRead:
        existing = self.repository.get_task(task_id=task_id, user_id=user_id)
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        if existing.status == TaskStatus.DONE:
            return TaskRead.from_model(existing)

        task = self.repository.complete_task(task_id=task_id, user_id=user_id, payload=payload)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        self.repository.log_task_event(
            user_id=user_id,
            event_type="task_completed",
            task_id=task.id,
            payload={"actual_minutes": payload.actual_minutes},
        )
        self.enqueue_memory_distillation(
            user_id=user_id,
            trigger_source="task_complete",
            entity_type="task",
            entity_id=task.id,
        )
        return TaskRead.from_model(task)

    def queue_due_soon_notification(self, *, user_id: str, task_id: str) -> tuple[object, object | None]:
        task = self.repository.get_task(task_id=task_id, user_id=user_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        notification_service = NotificationService(self.repository.connection)
        return notification_service.queue_task_due_soon_alert(task=task)
