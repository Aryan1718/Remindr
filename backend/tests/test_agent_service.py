from __future__ import annotations

import unittest
from datetime import UTC, date, datetime

from app.llm.schemas import LLMStructuredResult, LLMTextResult
from app.models.fatigue import FatigueEstimateModel, FatigueModeRecommendation, FatigueTimeBucket
from app.models.internal_calendar import CalendarBlockStatus, CalendarBlockType
from app.schemas.decision import (
    DayPlanResponse,
    DecisionNextBestActionRequest,
    DecisionResponse,
    DecisionSuggestedActionRead,
    DecisionSuggestionRead,
)
from app.schemas.fatigue import FatigueCheckinRead
from app.schemas.internal_calendar import InternalCalendarBlockRead
from app.schemas.task import TaskRead
from app.services.agent_service import AgentService, NormalizedTelegramInbound


class FakeLLMClient:
    def __init__(self, *, text: str = "This is an LLM reply.", structured: dict[str, dict] | None = None) -> None:
        self.text = text
        self.structured = structured or {}
        self.calls: list[dict] = []

    def generate_text(self, *, messages, model=None, temperature=0.2, max_tokens=None) -> LLMTextResult:
        self.calls.append(
            {
                "messages": messages,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return LLMTextResult(text=self.text)

    def generate_structured(self, *, messages, schema, model=None, temperature=0.0, max_tokens=None) -> LLMStructuredResult:
        self.calls.append(
            {
                "messages": messages,
                "schema": schema,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        prompt = messages[-1].content
        marker = 'Input: "'
        raw_text = prompt.split(marker)[-1].rstrip('"') if marker in prompt else prompt
        parsed = dict(self.structured.get(raw_text, {"intent_type": "GENERAL_DECISION"}))
        return LLMStructuredResult(parsed=parsed, text=str(parsed))


class FakeDecisionService:
    def __init__(self) -> None:
        self.query_calls: list[tuple[str, object]] = []
        self.plan_calls: list[tuple[str, object]] = []
        self.next_action_calls: list[tuple[str, object]] = []

    def query(self, *, user_id: str, payload) -> DecisionResponse:
        self.query_calls.append((user_id, payload))
        return DecisionResponse(
            decision_id="decision-1",
            mode="guided",
            primary_recommendation=DecisionSuggestionRead(
                task_id="task-1",
                title="Finish resume bullets",
                summary="This is the highest-leverage task tonight.",
                score=9.4,
                estimated_minutes=45,
            ),
            alternatives=[],
            reasoning_summary="It is short, important, and fits the time window.",
            confidence=0.88,
            follow_up_questions=[],
            suggested_actions=[DecisionSuggestedActionRead(action_type="task_done", label="Done", payload={"task_id": "task-1"})],
        )

    def next_best_action(self, *, user_id: str, payload: DecisionNextBestActionRequest) -> DecisionResponse:
        self.next_action_calls.append((user_id, payload))
        return self.query(user_id=user_id, payload=payload)

    def plan_day(self, *, user_id: str, payload) -> DayPlanResponse:
        self.plan_calls.append((user_id, payload))
        return DayPlanResponse(
            decision_id="plan-1",
            date=date(2026, 4, 19),
            mode="guided",
            summary="Start with one focused block, then handle lighter admin work.",
            recommendations=[
                DecisionSuggestionRead(
                    task_id="task-1",
                    title="Finish resume bullets",
                    summary="Best first block while energy is still usable.",
                    score=9.0,
                )
            ],
            recommended_blocks=[],
            suggested_actions=[],
        )


class FakeTaskService:
    def __init__(self) -> None:
        self.create_calls: list[tuple[str, object]] = []
        self.complete_calls: list[tuple[str, str, object]] = []
        self.list_calls: list[tuple[str, object]] = []

    def create_task(self, *, user_id: str, payload) -> TaskRead:
        self.create_calls.append((user_id, payload))
        return TaskRead(
            id="task-1",
            title=payload.title,
            description=None,
            priority=3,
            estimated_minutes=None,
            actual_minutes=None,
            energy_required=None,
            due_at=payload.due_at,
            status="pending",
            source=payload.source,
            metadata_json=payload.metadata_json,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            completed_at=None,
        )

    def complete_task(self, *, user_id: str, task_id: str, payload) -> TaskRead:
        self.complete_calls.append((user_id, task_id, payload))
        return TaskRead(
            id=task_id,
            title="Finish resume bullets",
            description=None,
            priority=3,
            estimated_minutes=45,
            actual_minutes=45,
            energy_required=2,
            due_at=None,
            status="done",
            source="telegram",
            metadata_json={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            completed_at=payload.completed_at,
        )

    def list_tasks(self, *, user_id: str, filters) -> list[TaskRead]:
        self.list_calls.append((user_id, filters))
        return [
            TaskRead(
                id="task-1",
                title="Finish resume bullets",
                description=None,
                priority=3,
                estimated_minutes=45,
                actual_minutes=None,
                energy_required=2,
                due_at=datetime(2026, 4, 20, 18, 0, tzinfo=UTC),
                status="pending",
                source="telegram",
                metadata_json={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                completed_at=None,
            )
        ]


class FakeFatigueService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def create_checkin(self, *, user_id: str, payload) -> FatigueCheckinRead:
        self.calls.append((user_id, payload))
        return FatigueCheckinRead(
            id="checkin-1",
            user_id=user_id,
            score=payload.score,
            source=payload.source,
            notes=payload.notes,
            context_json=payload.context_json,
            created_at=datetime.now(UTC),
        )

    def estimate_current_fatigue(self, *, user_id: str, timezone_name: str | None = None, at: datetime | None = None) -> FatigueEstimateModel:
        _ = (user_id, timezone_name, at)
        return FatigueEstimateModel(
            estimated_fatigue_score=2.0,
            time_bucket=FatigueTimeBucket.AFTERNOON,
            pattern_confidence=0.5,
            estimation_confidence=0.8,
            mode_recommendation=FatigueModeRecommendation.GUIDED,
        )


class FakeCalendarService:
    def __init__(self) -> None:
        self.confirm_calls: list[tuple[str, str, object]] = []
        self.reject_calls: list[tuple[str, str, object]] = []
        self.reschedule_calls: list[tuple[str, str, object]] = []
        self.list_calls: list[tuple[str, object]] = []

    def confirm_block(self, *, user_id: str, block_id: str, payload) -> InternalCalendarBlockRead:
        self.confirm_calls.append((user_id, block_id, payload))
        return self._block(block_id)

    def reject_block(self, *, user_id: str, block_id: str, payload) -> InternalCalendarBlockRead:
        self.reject_calls.append((user_id, block_id, payload))
        return self._block(block_id, status=CalendarBlockStatus.REJECTED)

    def reschedule_block(self, *, user_id: str, block_id: str, payload) -> InternalCalendarBlockRead:
        self.reschedule_calls.append((user_id, block_id, payload))
        return self._block(block_id, status=CalendarBlockStatus.RESCHEDULED)

    def list_blocks(self, *, user_id: str, filters) -> list[InternalCalendarBlockRead]:
        self.list_calls.append((user_id, filters))
        return [self._block("block-1")]

    def _block(self, block_id: str, status: CalendarBlockStatus = CalendarBlockStatus.CONFIRMED) -> InternalCalendarBlockRead:
        now = datetime(2026, 4, 19, 18, 0, tzinfo=UTC)
        return InternalCalendarBlockRead(
            id=block_id,
            task_id="task-1",
            title="Focus - Finish resume bullets",
            block_type=CalendarBlockType.SUGGESTED_TASK,
            starts_at=now,
            ends_at=now,
            status=status,
            sync_to_google=False,
            external_event_id=None,
            source="system",
            reason_summary=None,
            reschedule_count=1,
            priority_snapshot=3,
            energy_snapshot=2,
            metadata_json={},
            created_at=now,
            updated_at=now,
            confirmed_at=now,
            rejected_at=None,
            completed_at=None,
        )


class AgentServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decision_service = FakeDecisionService()
        self.task_service = FakeTaskService()
        self.fatigue_service = FakeFatigueService()
        self.calendar_service = FakeCalendarService()
        self.llm_client = FakeLLMClient()
        self.service = AgentService(
            connection=None,
            decision_service=self.decision_service,
            task_service=self.task_service,
            fatigue_service=self.fatigue_service,
            internal_calendar_service=self.calendar_service,
            llm_client=self.llm_client,
        )

    def test_next_action_routes_to_decision_service_and_formats_reply(self) -> None:
        self.llm_client.structured = {"What should I do first tonight?": {"intent_type": "NEXT_ACTION"}}
        reply = self.service.handle_telegram_inbound(
            user_id="user-1",
            inbound=NormalizedTelegramInbound(update_type="message", text="What should I do first tonight?"),
        )

        assert reply is not None
        self.assertEqual(reply.intent, "next_action")
        self.assertIn("Best task right now:", reply.text)
        self.assertEqual(reply.reply_markup["inline_keyboard"][0][0]["callback_data"], "task:done:task-1")
        self.assertEqual(self.decision_service.next_action_calls[0][0], "user-1")

    def test_create_task_routes_to_task_service(self) -> None:
        self.llm_client.structured = {
            "Remind me to finish resume bullets tomorrow": {
                "intent_type": "CREATE_TASK",
                "task_title": "Finish resume bullets",
            }
        }
        reply = self.service.handle_telegram_inbound(
            user_id="user-1",
            inbound=NormalizedTelegramInbound(update_type="message", text="Remind me to finish resume bullets tomorrow"),
        )

        assert reply is not None
        self.assertEqual(reply.intent, "create_task")
        self.assertEqual(self.task_service.create_calls[0][1].title, "Finish resume bullets")
        self.assertIn("Task saved:", reply.text)

    def test_deadline_task_can_create_and_recommend_next_action(self) -> None:
        due_at = datetime(2026, 4, 20, 17, 0, tzinfo=UTC)
        self.llm_client.structured = {
            "I have to finish the deck by Monday. Do you have anything for me now that I can do?": {
                "intent_type": "CREATE_TASK",
                "task_title": "Finish the deck",
                "due_at": due_at.isoformat(),
                "wants_recommendation_now": True,
            }
        }

        reply = self.service.handle_telegram_inbound(
            user_id="user-1",
            inbound=NormalizedTelegramInbound(
                update_type="message",
                text="I have to finish the deck by Monday. Do you have anything for me now that I can do?",
            ),
        )

        assert reply is not None
        self.assertEqual(reply.intent, "create_task_with_next_action")
        self.assertEqual(self.task_service.create_calls[0][1].title, "Finish the deck")
        self.assertEqual(self.task_service.create_calls[0][1].due_at, due_at)
        self.assertEqual(self.decision_service.next_action_calls[0][0], "user-1")
        self.assertIn("Task saved:", reply.text)
        self.assertIn("Best task right now:", reply.text)
        self.assertIn("Finish the deck", self.decision_service.next_action_calls[0][1].query)

    def test_fatigue_input_routes_to_fatigue_service(self) -> None:
        reply = self.service.handle_telegram_inbound(
            user_id="user-1",
            inbound=NormalizedTelegramInbound(update_type="message", text="Fatigue 4"),
        )

        assert reply is not None
        self.assertEqual(reply.intent, "fatigue_input")
        self.assertEqual(self.fatigue_service.calls[0][1].score, 4)
        self.assertIn("Logged fatigue as 4/5", reply.text)

    def test_callback_done_routes_to_task_service(self) -> None:
        reply = self.service.handle_telegram_inbound(
            user_id="user-1",
            inbound=NormalizedTelegramInbound(
                update_type="callback_query",
                callback_data="task:done:task-9",
                callback_query_id="cb-1",
            ),
        )

        assert reply is not None
        self.assertEqual(reply.intent, "task_complete")
        self.assertEqual(self.task_service.complete_calls[0][1], "task-9")
        self.assertEqual(reply.callback_notice, "Task marked done.")

    def test_calendar_move_callback_routes_to_internal_calendar_service(self) -> None:
        reply = self.service.handle_telegram_inbound(
            user_id="user-1",
            inbound=NormalizedTelegramInbound(
                update_type="callback_query",
                callback_data="calendar:move:block-1",
                callback_query_id="cb-1",
            ),
        )

        assert reply is not None
        self.assertEqual(reply.intent, "internal_calendar_action")
        self.assertEqual(self.calendar_service.reschedule_calls[0][1], "block-1")
        self.assertIn("Moved: Focus - Finish resume bullets.", reply.text)

    def test_get_tasks_routes_to_task_service(self) -> None:
        self.llm_client.structured = {"Show my tasks": {"intent_type": "GET_TASKS"}}
        reply = self.service.handle_telegram_inbound(
            user_id="user-1",
            inbound=NormalizedTelegramInbound(update_type="message", text="Show my tasks"),
        )

        assert reply is not None
        self.assertEqual(reply.intent, "get_tasks")
        self.assertIn("Open tasks:", reply.text)
        self.assertEqual(self.task_service.list_calls[1][0], "user-1")

    def test_plan_day_routes_to_decision_service(self) -> None:
        self.llm_client.structured = {"Plan my day": {"intent_type": "PLAN_DAY"}}
        reply = self.service.handle_telegram_inbound(
            user_id="user-1",
            inbound=NormalizedTelegramInbound(update_type="message", text="Plan my day"),
        )

        assert reply is not None
        self.assertEqual(reply.intent, "plan_day")
        self.assertEqual(self.decision_service.plan_calls[0][0], "user-1")
        self.assertIn("Plan for today:", reply.text)

    def test_calendar_action_routes_to_calendar_service(self) -> None:
        self.llm_client.structured = {"Show my calendar": {"intent_type": "CALENDAR_ACTION"}}
        reply = self.service.handle_telegram_inbound(
            user_id="user-1",
            inbound=NormalizedTelegramInbound(update_type="message", text="Show my calendar"),
        )

        assert reply is not None
        self.assertEqual(reply.intent, "calendar_action")
        self.assertEqual(self.calendar_service.list_calls[1][0], "user-1")
        self.assertIn("Next calendar blocks:", reply.text)

    def test_unknown_intent_falls_back_to_general_decision(self) -> None:
        self.llm_client.structured = {"Tell me something useful": {"intent_type": "UNKNOWN"}}
        reply = self.service.handle_telegram_inbound(
            user_id="user-1",
            inbound=NormalizedTelegramInbound(update_type="message", text="Tell me something useful"),
        )

        assert reply is not None
        self.assertEqual(reply.intent, "general_decision")
        self.assertEqual(self.decision_service.query_calls[0][0], "user-1")
        self.assertIn("Finish resume bullets", reply.text)


if __name__ == "__main__":
    unittest.main()
