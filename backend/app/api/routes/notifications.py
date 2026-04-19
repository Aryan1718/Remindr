from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends

from app.core.db import get_db_connection
from app.core.security import AuthenticatedUser, get_current_user
from app.schemas.notification import (
    NotificationCreateRequest,
    NotificationDismissRequest,
    NotificationEnvelope,
    NotificationListEnvelope,
    NotificationListFilters,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications")


def get_notification_service(
    connection: psycopg.Connection = Depends(get_db_connection),
) -> NotificationService:
    return NotificationService(connection)


@router.get("", response_model=NotificationListEnvelope)
def list_notifications(
    filters: NotificationListFilters = Depends(),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationListEnvelope:
    items = service.list_notifications(user_id=current_user.user_id, filters=filters)
    return NotificationListEnvelope(
        data={"items": items},
        meta={"count": len(items), "next_cursor": None},
    )


@router.post("/test", response_model=NotificationEnvelope)
def create_test_notification(
    payload: NotificationCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationEnvelope:
    notification, job = service.create_test_notification(user_id=current_user.user_id, payload=payload)
    return NotificationEnvelope(
        data={
            "notification": notification,
            "delivery_status": "queued",
            "job_id": getattr(job, "job_id", None),
        },
        message="Notification queued",
    )


@router.post("/{notification_id}/dismiss", response_model=NotificationEnvelope)
def dismiss_notification(
    notification_id: str,
    _: NotificationDismissRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationEnvelope:
    notification = service.dismiss_notification(user_id=current_user.user_id, notification_id=notification_id)
    return NotificationEnvelope(
        data={"notification_id": notification.id, "status": notification.status},
        message="Notification dismissed",
    )
