from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.routes.notifications import get_notification_service
from app.core.security import AuthenticatedUser, get_current_user
from app.main import create_app
from app.models.notification import NotificationChannel, NotificationStatus
from app.schemas.notification import NotificationCreateRequest, NotificationRead


class FakeNotificationRouteService:
    def list_notifications(self, *, user_id: str, filters) -> list[NotificationRead]:
        assert user_id == "user-1"
        return [
            NotificationRead(
                id="notification-1",
                task_id=None,
                calendar_block_id=None,
                channel=NotificationChannel.TELEGRAM,
                title="Reminder",
                body="Check your plan",
                scheduled_for=datetime.now(UTC),
                sent_at=None,
                status=NotificationStatus.QUEUED,
                provider_message_id=None,
                metadata_json={"kind": "generic_reminder"},
                created_at=datetime.now(UTC),
            )
        ]

    def create_test_notification(self, *, user_id: str, payload: NotificationCreateRequest):
        assert user_id == "user-1"
        notification = NotificationRead(
            id="notification-2",
            task_id=None,
            calendar_block_id=None,
            channel=NotificationChannel.TELEGRAM,
            title=payload.title,
            body=payload.body,
            scheduled_for=datetime.now(UTC),
            sent_at=None,
            status=NotificationStatus.QUEUED,
            provider_message_id=None,
            metadata_json={"kind": "generic_reminder"},
            created_at=datetime.now(UTC),
        )
        job = type("Job", (), {"job_id": "job-1"})()
        return notification, job

    def dismiss_notification(self, *, user_id: str, notification_id: str) -> NotificationRead:
        assert user_id == "user-1"
        return NotificationRead(
            id=notification_id,
            task_id=None,
            calendar_block_id=None,
            channel=NotificationChannel.TELEGRAM,
            title=None,
            body="Dismiss me",
            scheduled_for=None,
            sent_at=None,
            status=NotificationStatus.DISMISSED,
            provider_message_id=None,
            metadata_json={},
            created_at=datetime.now(UTC),
        )


def test_list_notifications_route_returns_items() -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(user_id="user-1", auth_user_id="auth-1")
    app.dependency_overrides[get_notification_service] = lambda: FakeNotificationRouteService()
    client = TestClient(app)

    response = client.get("/api/v1/notifications")

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["count"] == 1
    assert body["data"]["items"][0]["id"] == "notification-1"


def test_create_test_notification_route_returns_queued_status() -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(user_id="user-1", auth_user_id="auth-1")
    app.dependency_overrides[get_notification_service] = lambda: FakeNotificationRouteService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/notifications/test",
        json={"channel": "telegram", "title": "Test", "body": "This is a test notification"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["delivery_status"] == "queued"
    assert body["data"]["notification"]["id"] == "notification-2"


def test_dismiss_notification_route_marks_dismissed() -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(user_id="user-1", auth_user_id="auth-1")
    app.dependency_overrides[get_notification_service] = lambda: FakeNotificationRouteService()
    client = TestClient(app)

    response = client.post("/api/v1/notifications/notification-2/dismiss", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["notification_id"] == "notification-2"
    assert body["data"]["status"] == "dismissed"
