from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, status

from app.core.db import get_db_connection
from app.core.security import AuthenticatedUser, get_current_user
from app.schemas.task import (
    CompleteTaskRequest,
    TaskCreateRequest,
    TaskEnvelope,
    TaskFilters,
    TaskListEnvelope,
    TaskUpdateRequest,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks")


def get_task_service(connection: psycopg.Connection = Depends(get_db_connection)) -> TaskService:
    return TaskService(connection)


@router.post("", response_model=TaskEnvelope, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
) -> TaskEnvelope:
    task = service.create_task(user_id=current_user.user_id, payload=payload)
    return TaskEnvelope(data={"task": task}, message="Task created")


@router.get("", response_model=TaskListEnvelope)
def list_tasks(
    filters: TaskFilters = Depends(),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
) -> TaskListEnvelope:
    items = service.list_tasks(user_id=current_user.user_id, filters=filters)
    return TaskListEnvelope(
        data={"items": items},
        meta={"count": len(items), "next_cursor": None},
    )


@router.get("/{task_id}", response_model=TaskEnvelope)
def get_task(
    task_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
) -> TaskEnvelope:
    task = service.get_task(user_id=current_user.user_id, task_id=task_id)
    return TaskEnvelope(data={"task": task, "calendar_blocks": []})


@router.patch("/{task_id}", response_model=TaskEnvelope)
def update_task(
    task_id: str,
    payload: TaskUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
) -> TaskEnvelope:
    task = service.update_task(user_id=current_user.user_id, task_id=task_id, payload=payload)
    return TaskEnvelope(data={"task": task}, message="Task updated")


@router.post("/{task_id}/complete", response_model=TaskEnvelope)
def complete_task(
    task_id: str,
    payload: CompleteTaskRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
) -> TaskEnvelope:
    task = service.complete_task(user_id=current_user.user_id, task_id=task_id, payload=payload)
    return TaskEnvelope(data={"task": task}, message="Task completed")
