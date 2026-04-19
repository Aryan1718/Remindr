from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.routes.decisions import get_decision_service
from app.core.security import AuthenticatedUser, get_current_user
from app.main import create_app
from app.schemas.decision import DecisionNextBestActionRequest, DecisionQueryRequest
from app.services.decision_service import DecisionService
from app.models.user import UserModel, UserPreferencesModel
from tests.test_decision_service import (
    FakeCalendarRepository,
    FakeFatigueService,
    FakeTaskRepository,
    FakeUserRepository,
    build_task,
)


def build_route_service() -> DecisionService:
    user = UserModel(
        id="user-1",
        auth_user_id="auth-1",
        email="user@example.com",
        full_name="User",
        timezone="UTC",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    preferences = UserPreferencesModel(id="pref-1", user_id="user-1", fatigue_prompt_enabled=True)
    return DecisionService(
        task_repository=FakeTaskRepository(
            [
                build_task(task_id="a", due_in_hours=4, priority=4, estimated_minutes=30, energy_required=2),
                build_task(task_id="b", due_in_hours=24, priority=3, estimated_minutes=30, energy_required=2),
            ]
        ),
        calendar_repository=FakeCalendarRepository([]),
        user_repository=FakeUserRepository(user, preferences),
        fatigue_service=FakeFatigueService(score=4),
    )


def test_decision_query_route_returns_decisive_mode() -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(user_id="user-1", auth_user_id="auth-1")
    app.dependency_overrides[get_decision_service] = build_route_service
    client = TestClient(app)

    response = client.post(
        "/api/v1/decision/query",
        json=DecisionQueryRequest(query="What should I do first tonight?").model_dump(mode="json"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["mode"] == "decisive"
    assert body["data"]["primary_recommendation"]["task_id"] == "a"


def test_next_best_action_route_returns_single_recommendation() -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(user_id="user-1", auth_user_id="auth-1")
    app.dependency_overrides[get_decision_service] = build_route_service
    client = TestClient(app)

    response = client.post(
        "/api/v1/decision/next-best-action",
        json=DecisionNextBestActionRequest(time_available_minutes=30).model_dump(mode="json"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["primary_recommendation"]["task_id"] == "a"
    assert body["data"]["alternatives"] == []
