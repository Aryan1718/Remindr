from __future__ import annotations

import unittest
from datetime import UTC, date, datetime

from app.llm.schemas import LLMTextResult
from app.models.internal_calendar import CalendarBlockStatus, CalendarBlockType
from app.schemas.decision import (
    DayPlanResponse,
    DecisionResponse,
    DecisionSuggestedActionRead,
    DecisionSuggestionRead,
)
from app.schemas.fatigue import FatigueCheckinRead
from app.schemas.internal_calendar import InternalCalendarBlockRead
from app.schemas.task import TaskRead
from app.services.agent_service import AgentService, NormalizedTelegramInbound


class FakeLLMClient:
    def __init__(self, text: str = "This is an LLM reply.") -> None:
        self.text = text
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


class FakeDecisionService:
    def __init__(self) -> None:
        self.query_calls: list[tuple[str, object]] = []
        self.plan_calls: list[tuple[str, object]] = []

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
            due_at=None,
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


class FakeCalendarService:
    def __init__(self) -> None:
        self.confirm_calls: list[tuple[str, str, object]] = []
        self.reject_calls: list[tuple[str, str, object]] = []
        self.reschedule_calls: list[tuple[str, str, object]] = []

    def confirm_block(self, *, user_id: str, block_id: str, payload) -> InternalCalendarBlockRead:
        self.confirm_calls.append((user_id, block_id, payload))
        return self._block(block_id)

    def reject_block(self, *, user_id: str, block_id: str, payload) -> InternalCalendarBlockRead:
        self.reject_calls.append((user_id, block_id, payload))
        return self._block(block_id, status=CalendarBlockStatus.REJECTED)

    def reschedule_block(self, *, user_id: str, block_id: str, payload) -> InternalCalendarBlockRead:
        self.reschedule_calls.append((user_id, block_id, payload))
        return self._block(block_id, status=CalendarBlockStatus.RESCHEDULED)

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
        self.service = AgentService(
            connection=None,
            decision_service=self.decision_service,
            task_service=self.task_service,
            fatigue_service=self.fatigue_service,
            internal_calendar_service=self.calendar_service,
        )

    def test_decision_query_routes_to_decision_service_and_formats_reply(self) -> None:
        reply = self.service.handle_telegram_inbound(
            user_id="user-1",
            inbound=NormalizedTelegramInbound(update_type="message", text="What should I do first tonight?"),
        )

        assert reply is not None
        self.assertEqual(reply.intent, "decision_query")
        self.assertIn("First: Finish resume bullets.", reply.text)
        self.assertEqual(reply.reply_markup["inline_keyboard"][0][0]["callback_data"], "task:done:task-1")
        self.assertEqual(self.decision_service.query_calls[0][0], "user-1")

    def test_task_capture_routes_to_task_service(self) -> None:
        reply = self.service.handle_telegram_inbound(
            user_id="user-1",
            inbound=NormalizedTelegramInbound(update_type="message", text="Task: finish resume bullets"),
        )

        assert reply is not None
        self.assertEqual(reply.intent, "task_capture")
        self.assertEqual(self.task_service.create_calls[0][1].title, "finish resume bullets")
        self.assertIn("Captured task", reply.text)

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

    def test_general_question_routes_to_llm_reply(self) -> None:
        llm_client = FakeLLMClient(text="Paris is the capital of France.")
        service = AgentService(
            connection=None,
            decision_service=self.decision_service,
            task_service=self.task_service,
            fatigue_service=self.fatigue_service,
            internal_calendar_service=self.calendar_service,
            llm_client=llm_client,
        )

        reply = service.handle_telegram_inbound(
            user_id="user-1",
            inbound=NormalizedTelegramInbound(update_type="message", text="What is the capital of France?"),
        )

        assert reply is not None
        self.assertEqual(reply.intent, "general_chat")
        self.assertEqual(reply.text, "Paris is the capital of France.")
        self.assertEqual(len(self.decision_service.query_calls), 0)
        self.assertEqual(llm_client.calls[0]["messages"][1].content, "What is the capital of France?")

    def test_non_command_statement_routes_to_llm_reply(self) -> None:
        llm_client = FakeLLMClient(text="I can help with that.")
        service = AgentService(
            connection=None,
            decision_service=self.decision_service,
            task_service=self.task_service,
            fatigue_service=self.fatigue_service,
            internal_calendar_service=self.calendar_service,
            llm_client=llm_client,
        )

        reply = service.handle_telegram_inbound(
            user_id="user-1",
            inbound=NormalizedTelegramInbound(update_type="message", text="Tell me a quick joke"),
        )

        assert reply is not None
        self.assertEqual(reply.intent, "general_chat")
        self.assertEqual(reply.text, "I can help with that.")
        self.assertEqual(len(self.decision_service.query_calls), 0)


if __name__ == "__main__":
    unittest.main()
