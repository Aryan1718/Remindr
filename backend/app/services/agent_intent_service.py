from __future__ import annotations

from app.core.config import Settings, get_settings
from app.llm import get_llm_client
from app.llm.base import BaseLLMClient
from app.llm.schemas import ChatMessage, StructuredOutputSchema
from app.services.agent_intent_schema import NormalizedIntent


INTENT_SCHEMA = StructuredOutputSchema(
    name="normalized_intent",
    json_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "intent_type": {
                "type": "string",
                "enum": [
                    "CREATE_TASK",
                    "GET_TASKS",
                    "NEXT_ACTION",
                    "PLAN_DAY",
                    "GENERAL_DECISION",
                    "CALENDAR_ACTION",
                    "UNKNOWN",
                ],
            },
            "entities": {"type": "object", "additionalProperties": True},
            "context": {"type": "object", "additionalProperties": True},
            "task_title": {"type": ["string", "null"]},
            "due_at": {"type": ["string", "null"], "format": "date-time"},
            "time_available_minutes": {"type": ["integer", "null"], "minimum": 0, "maximum": 720},
            "fatigue_score": {"type": ["integer", "null"], "minimum": 0, "maximum": 5},
        },
        "required": ["intent_type"],
    },
)


class AgentIntentService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        llm_client: BaseLLMClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm_client = llm_client if llm_client is not None else get_llm_client(self.settings)

    async def normalize_intent(self, user_message: str) -> NormalizedIntent:
        message = user_message.strip()
        if not message:
            return NormalizedIntent(intent_type="UNKNOWN", raw_text=user_message)

        if self.llm_client is None:
            return self._fallback_normalize(message)

        try:
            result = self.llm_client.generate_structured(
                messages=[
                    ChatMessage(
                        role="system",
                        content=(
                            "You are an intent parser for a productivity assistant.\n"
                            "Convert user input into structured intent.\n"
                            "Be minimal and accurate.\n"
                            "Return strict JSON only.\n"
                            "Do not hallucinate missing fields."
                        ),
                    ),
                    ChatMessage(
                        role="user",
                        content=(
                            "Examples:\n"
                            'Input: "I am free right now what should I do"\n'
                            'Output: {"intent_type":"NEXT_ACTION","time_available_minutes":null}\n'
                            'Input: "Remind me to finish assignment tomorrow"\n'
                            'Output: {"intent_type":"CREATE_TASK","task_title":"Finish assignment","due_at":"2026-04-20T09:00:00Z"}\n'
                            f'Input: "{message}"'
                        ),
                    ),
                ],
                schema=INTENT_SCHEMA,
                temperature=0.0,
                max_tokens=240,
            )
            payload = dict(result.parsed)
            payload["raw_text"] = user_message
            payload.setdefault("entities", {})
            payload.setdefault("context", {})
            return NormalizedIntent.model_validate(payload)
        except Exception:
            return self._fallback_normalize(message)

    def _fallback_normalize(self, message: str) -> NormalizedIntent:
        lowered = message.casefold()
        if lowered.startswith(("task:", "todo:", "add task:", "capture task:", "remind me to ")):
            title = message.split(":", 1)[1].strip() if ":" in message else message[13:].strip()
            return NormalizedIntent(intent_type="CREATE_TASK", raw_text=message, task_title=title or None)
        if "plan my day" in lowered or "plan today" in lowered or "plan tomorrow" in lowered:
            return NormalizedIntent(intent_type="PLAN_DAY", raw_text=message)
        if any(phrase in lowered for phrase in ("what should i do", "what next", "what now", "what should i work on")):
            return NormalizedIntent(intent_type="NEXT_ACTION", raw_text=message)
        if "calendar" in lowered or "schedule" in lowered:
            return NormalizedIntent(intent_type="CALENDAR_ACTION", raw_text=message)
        if any(phrase in lowered for phrase in ("list tasks", "show tasks", "my tasks", "what tasks")):
            return NormalizedIntent(intent_type="GET_TASKS", raw_text=message)
        return NormalizedIntent(intent_type="GENERAL_DECISION", raw_text=message)


async def normalize_intent(
    user_message: str,
    *,
    settings: Settings | None = None,
    llm_client: BaseLLMClient | None = None,
) -> NormalizedIntent:
    service = AgentIntentService(settings=settings, llm_client=llm_client)
    return await service.normalize_intent(user_message)
