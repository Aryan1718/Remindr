from __future__ import annotations

import psycopg
from fastapi import HTTPException, status

from app.repositories.tasks import TaskRepository
from app.schemas.task import CompleteTaskRequest, TaskCreateRequest, TaskFilters, TaskRead, TaskUpdateRequest


class TaskService:
    def __init__(self, connection: psycopg.Connection) -> None:
        self.repository = TaskRepository(connection)

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
        task = self.repository.complete_task(task_id=task_id, user_id=user_id, payload=payload)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        self.repository.log_task_event(
            user_id=user_id,
            event_type="task_completed",
            task_id=task.id,
            payload={"actual_minutes": payload.actual_minutes},
        )
        return TaskRead.from_model(task)
