from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
from fastapi import HTTPException

from app.core.config import Settings, get_settings
from app.llm import get_llm_client
from app.llm.base import BaseLLMClient
from app.llm.schemas import ChatMessage
from app.schemas.decision import DecisionPlanDayRequest, DecisionQueryRequest
from app.schemas.fatigue import FatigueCheckinCreateRequest
from app.schemas.internal_calendar import (
    InternalCalendarConfirmRequest,
    InternalCalendarRejectRequest,
    InternalCalendarRescheduleRequest,
)
from app.schemas.task import CompleteTaskRequest, TaskCreateRequest
from app.services.decision_service import DecisionService
from app.services.fatigue_service import FatigueService
from app.services.internal_calendar_service import InternalCalendarService
from app.services.task_service import TaskService

FATIGUE_PATTERNS = (
    re.compile(r"\bfatigue\b\s*[:=]?\s*([0-5])\b", re.IGNORECASE),
    re.compile(r"\benergy\b\s*[:=]?\s*([0-5])\b", re.IGNORECASE),
    re.compile(r"\bi(?: am|'m)\s+(?:at\s+)?([0-5])\s*/?\s*5\b", re.IGNORECASE),
)


@dataclass(slots=True)
class NormalizedTelegramInbound:
    update_type: str
    text: str | None = None
    callback_data: str | None = None
    callback_query_id: str | None = None
    telegram_chat_id: int | None = None
    telegram_user_id: int | None = None


@dataclass(slots=True)
class TelegramAgentReply:
    text: str
    intent: str
    reply_markup: dict[str, Any] | None = None
    callback_notice: str | None = None


@dataclass(slots=True)
class TelegramCallbackAction:
    namespace: str
    action: str
    entity_id: str | None = None
    value: str | None = None


class AgentService:
    def __init__(
        self,
        connection: psycopg.Connection | None = None,
        *,
        settings: Settings | None = None,
        decision_service: DecisionService | None = None,
        task_service: TaskService | None = None,
        fatigue_service: FatigueService | None = None,
        internal_calendar_service: InternalCalendarService | None = None,
        llm_client: BaseLLMClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.decision_service = decision_service or self._maybe_build(DecisionService, connection)
        self.task_service = task_service or self._maybe_build(TaskService, connection)
        self.fatigue_service = fatigue_service or self._maybe_build(FatigueService, connection)
        self.internal_calendar_service = internal_calendar_service or self._maybe_build(InternalCalendarService, connection)
        self.llm_client = llm_client if llm_client is not None else get_llm_client(self.settings)

    def handle_telegram_inbound(self, *, user_id: str, inbound: NormalizedTelegramInbound) -> TelegramAgentReply | None:
        if inbound.update_type == "callback_query" and inbound.callback_data:
            return self.handle_callback(user_id=user_id, inbound=inbound)

        message_text = (inbound.text or "").strip()
        if not message_text:
            return None

        intent = self.classify_intent(message_text)
        if intent == "task_capture":
            return self._handle_task_capture(user_id=user_id, text=message_text)
        if intent == "fatigue_input":
            return self._handle_fatigue_input(user_id=user_id, text=message_text)
        if intent == "plan_request":
            return self._handle_plan_request(user_id=user_id)
        if intent == "decision_query":
            return self._handle_decision_query(user_id=user_id, text=message_text)
        if intent == "help_status":
            return self._handle_help_status()
        return self._handle_general_chat(user_id=user_id, text=message_text)

    def classify_intent(self, text: str) -> str:
        normalized = text.strip().lower()
        if normalized in {"/help", "help", "/status", "status"}:
            return "help_status"
        if normalized.startswith(("task:", "todo:", "add task:", "capture task:")):
            return "task_capture"
        if normalized.startswith("remind me to "):
            return "task_capture"
        if self._extract_fatigue_score(text) is not None:
            return "fatigue_input"
        if any(phrase in normalized for phrase in ("plan my day", "plan today", "plan tomorrow", "today plan", "tomorrow plan")):
            return "plan_request"
        if any(
            phrase in normalized
            for phrase in (
                "what should i do",
                "what should i work on",
                "what should i do first",
                "what do i do first",
                "what next",
                "what now",
                "should i",
                "which task",
            )
        ):
            return "decision_query"
        if normalized.endswith("?"):
            return "decision_query"
        return "help_status"

    def parse_callback_data(self, data: str) -> TelegramCallbackAction:
        parts = [part.strip() for part in data.split(":")]
        if len(parts) < 2 or not parts[0] or not parts[1]:
            raise HTTPException(status_code=400, detail="Unsupported Telegram callback payload")
        if parts[0] == "fatigue" and parts[1] == "score":
            if len(parts) != 3:
                raise HTTPException(status_code=400, detail="Fatigue callback payload is invalid")
            return TelegramCallbackAction(namespace="fatigue", action="score", value=parts[2])
        if len(parts) != 3:
            raise HTTPException(status_code=400, detail="Telegram callback payload is invalid")
        return TelegramCallbackAction(namespace=parts[0], action=parts[1], entity_id=parts[2])

    def handle_callback(self, *, user_id: str, inbound: NormalizedTelegramInbound) -> TelegramAgentReply:
        assert inbound.callback_data is not None
        callback = self.parse_callback_data(inbound.callback_data)

        if callback.namespace == "calendar" and callback.action == "confirm":
            service = self._require_service(self.internal_calendar_service, "internal calendar")
            block = service.confirm_block(
                user_id=user_id,
                block_id=callback.entity_id or "",
                payload=InternalCalendarConfirmRequest(reason_text="Confirmed from Telegram"),
            )
            return TelegramAgentReply(
                text=f"Confirmed: {block.title}. I’ll treat this block as planned.",
                intent="internal_calendar_action",
                callback_notice="Block confirmed.",
            )

        if callback.namespace == "calendar" and callback.action == "reject":
            service = self._require_service(self.internal_calendar_service, "internal calendar")
            block = service.reject_block(
                user_id=user_id,
                block_id=callback.entity_id or "",
                payload=InternalCalendarRejectRequest(reason_code="telegram_reject", reason_text="Rejected from Telegram"),
            )
            return TelegramAgentReply(
                text=f"Rejected: {block.title}. I’ll use that as feedback for later suggestions.",
                intent="internal_calendar_action",
                callback_notice="Block rejected.",
            )

        if callback.namespace == "calendar" and callback.action in {"move", "snooze"}:
            service = self._require_service(self.internal_calendar_service, "internal calendar")
            block = service.reschedule_block(
                user_id=user_id,
                block_id=callback.entity_id or "",
                payload=InternalCalendarRescheduleRequest(
                    auto_find_new_slot=True,
                    reason_code=f"telegram_{callback.action}",
                    reason_text=f"{callback.action.title()} from Telegram",
                ),
            )
            verb = "Snoozed" if callback.action == "snooze" else "Moved"
            return TelegramAgentReply(
                text=f"{verb}: {block.title}. New time: {self._format_datetime(block.starts_at)} to {self._format_datetime(block.ends_at)}.",
                intent="internal_calendar_action",
                callback_notice=f"Block {callback.action}d.",
            )

        if callback.namespace == "task" and callback.action == "done":
            service = self._require_service(self.task_service, "task")
            task = service.complete_task(
                user_id=user_id,
                task_id=callback.entity_id or "",
                payload=CompleteTaskRequest(completed_at=datetime.now(UTC)),
            )
            return TelegramAgentReply(
                text=f"Marked done: {task.title}.",
                intent="task_complete",
                callback_notice="Task marked done.",
            )

        if callback.namespace == "fatigue" and callback.action == "score":
            try:
                score = int(callback.value or "")
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Fatigue callback score is invalid") from exc
            service = self._require_service(self.fatigue_service, "fatigue")
            checkin = service.create_checkin(
                user_id=user_id,
                payload=FatigueCheckinCreateRequest(
                    score=score,
                    source="telegram",
                    context_json={"channel": "telegram", "input": "callback"},
                ),
            )
            return TelegramAgentReply(
                text=f"Saved fatigue score {checkin.score}/5.",
                intent="fatigue_input",
                callback_notice="Fatigue saved.",
            )

        raise HTTPException(status_code=400, detail="Unsupported Telegram callback action")

    def build_task_reply_markup(self, *, task_id: str) -> dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {"text": "Done", "callback_data": f"task:done:{task_id}"},
                ]
            ]
        }

    def build_calendar_reply_markup(self, *, block_id: str) -> dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {"text": "Confirm", "callback_data": f"calendar:confirm:{block_id}"},
                    {"text": "Move", "callback_data": f"calendar:move:{block_id}"},
                    {"text": "Reject", "callback_data": f"calendar:reject:{block_id}"},
                ]
            ]
        }

    def build_fatigue_reply_markup(self) -> dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {"text": str(score), "callback_data": f"fatigue:score:{score}"}
                    for score in range(0, 3)
                ],
                [
                    {"text": str(score), "callback_data": f"fatigue:score:{score}"}
                    for score in range(3, 6)
                ],
            ]
        }

    def _handle_task_capture(self, *, user_id: str, text: str) -> TelegramAgentReply:
        service = self._require_service(self.task_service, "task")
        title = self._extract_task_title(text)
        task = service.create_task(
            user_id=user_id,
            payload=TaskCreateRequest(
                title=title,
                source="telegram",
                metadata_json={"captured_via": "telegram"},
            ),
        )
        return TelegramAgentReply(
            text=f"Captured task: {task.title}.",
            intent="task_capture",
            reply_markup=self.build_task_reply_markup(task_id=task.id),
        )

    def _handle_fatigue_input(self, *, user_id: str, text: str) -> TelegramAgentReply:
        service = self._require_service(self.fatigue_service, "fatigue")
        score = self._extract_fatigue_score(text)
        if score is None:
            raise HTTPException(status_code=422, detail="Could not find a fatigue score from 0 to 5")
        checkin = service.create_checkin(
            user_id=user_id,
            payload=FatigueCheckinCreateRequest(
                score=score,
                source="telegram",
                notes=text,
                context_json={"channel": "telegram", "input": "message"},
            ),
        )
        return TelegramAgentReply(
            text=f"Logged fatigue as {checkin.score}/5. I’ll use that for the next recommendation.",
            intent="fatigue_input",
        )

    def _handle_plan_request(self, *, user_id: str) -> TelegramAgentReply:
        service = self._require_service(self.decision_service, "decision")
        plan = service.plan_day(
            user_id=user_id,
            payload=DecisionPlanDayRequest(),
        )
        lines = [plan.summary]
        for block in plan.recommendations[:2]:
            lines.append(f"- {block.title}: {block.summary}")
        return TelegramAgentReply(
            text="\n".join(lines),
            intent="plan_request",
        )

    def _handle_decision_query(self, *, user_id: str, text: str) -> TelegramAgentReply:
        service = self._require_service(self.decision_service, "decision")
        response = service.query(user_id=user_id, payload=DecisionQueryRequest(query=text))
        lines = [
            f"First: {response.primary_recommendation.title}.",
            response.primary_recommendation.summary,
            response.reasoning_summary,
        ]
        reply_markup = None
        if response.primary_recommendation.task_id:
            reply_markup = self.build_task_reply_markup(task_id=response.primary_recommendation.task_id)
        return TelegramAgentReply(
            text="\n".join(line for line in lines if line),
            intent="decision_query",
            reply_markup=reply_markup,
        )

    def _handle_help_status(self) -> TelegramAgentReply:
        return TelegramAgentReply(
            text=(
                "I can help you choose the next task, capture a task, log fatigue, and handle quick actions.\n"
                "Examples:\n"
                '- "What should I do first tonight?"\n'
                '- "Task: finish resume bullets"\n'
                '- "Fatigue 4"'
            ),
            intent="help_status",
            reply_markup=self.build_fatigue_reply_markup(),
        )

    def _handle_general_chat(self, *, user_id: str, text: str) -> TelegramAgentReply:
        if self.llm_client is None:
            return self._handle_help_status()

        service = self._require_service(self.decision_service, "decision")
        decision = service.query(user_id=user_id, payload=DecisionQueryRequest(query=text))
        result = self.llm_client.generate_text(
            messages=[
                ChatMessage(
                    role="system",
                    content=(
                        "You are a Telegram productivity assistant. Keep replies concise, natural, and grounded in the provided backend result. "
                        "Do not invent tasks, schedule changes, or memory."
                    ),
                ),
                ChatMessage(
                    role="user",
                    content=(
                        f"User message: {text}\n"
                        f"Primary recommendation: {decision.primary_recommendation.title}\n"
                        f"Recommendation summary: {decision.primary_recommendation.summary}\n"
                        f"Reasoning summary: {decision.reasoning_summary}"
                    ),
                ),
            ],
            temperature=0.2,
            max_tokens=180,
        )
        return TelegramAgentReply(
            text=result.text or f"First: {decision.primary_recommendation.title}. {decision.primary_recommendation.summary}",
            intent="decision_query",
            reply_markup=self.build_task_reply_markup(task_id=decision.primary_recommendation.task_id)
            if decision.primary_recommendation.task_id
            else None,
        )

    def _extract_task_title(self, text: str) -> str:
        normalized = text.strip()
        for prefix in ("task:", "todo:", "add task:", "capture task:"):
            if normalized.lower().startswith(prefix):
                value = normalized[len(prefix):].strip()
                return value or "Untitled task"
        if normalized.lower().startswith("remind me to "):
            value = normalized[13:].strip()
            return value or "Untitled task"
        return normalized

    def _extract_fatigue_score(self, text: str) -> int | None:
        for pattern in FATIGUE_PATTERNS:
            match = pattern.search(text)
            if match:
                return int(match.group(1))
        lowered = text.strip().lower()
        if lowered in {"tired", "exhausted", "drained"}:
            return 4
        return None

    def _format_datetime(self, value: datetime) -> str:
        local_value = value.astimezone(UTC)
        return local_value.strftime("%Y-%m-%d %H:%M UTC")

    def _maybe_build(self, cls, connection: psycopg.Connection | None):
        if connection is None:
            return None
        return cls(connection)

    def _require_service(self, service: Any, name: str):
        if service is None:
            raise RuntimeError(f"{name} service is not configured")
        return service
