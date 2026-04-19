from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.models.notification import NotificationModel


@dataclass(slots=True)
class TelegramDispatchPayload:
    text: str
    reply_markup: dict[str, Any] | None = None


class TelegramNotificationDispatcher:
    def build_payload(self, notification: NotificationModel) -> TelegramDispatchPayload:
        kind = str((notification.metadata_json or {}).get("kind") or "generic_reminder")
        if kind == "internal_calendar_suggestion":
            return self._build_internal_calendar_payload(notification)
        if kind == "task_due_soon":
            return self._build_task_due_soon_payload(notification)
        if kind == "fatigue_check_prompt":
            return self._build_fatigue_prompt_payload(notification)
        return self._build_generic_payload(notification)

    def _build_generic_payload(self, notification: NotificationModel) -> TelegramDispatchPayload:
        lines: list[str] = []
        if notification.title:
            lines.append(notification.title.strip())
        lines.append(notification.body.strip())
        return TelegramDispatchPayload(text="\n\n".join(part for part in lines if part), reply_markup=None)

    def _build_internal_calendar_payload(self, notification: NotificationModel) -> TelegramDispatchPayload:
        metadata = notification.metadata_json or {}
        title = metadata.get("block_title") or notification.title or "Calendar reminder"
        when_text = self._format_when(metadata.get("starts_at"), metadata.get("timezone"))
        lines = [
            f"Upcoming block: {title}",
            when_text,
            notification.body.strip(),
        ]
        block_id = notification.calendar_block_id or str(metadata.get("calendar_block_id") or "")
        return TelegramDispatchPayload(
            text="\n".join(line for line in lines if line),
            reply_markup={
                "inline_keyboard": [
                    [
                        {"text": "Confirm", "callback_data": f"calendar:confirm:{block_id}"},
                        {"text": "Move", "callback_data": f"calendar:move:{block_id}"},
                        {"text": "Reject", "callback_data": f"calendar:reject:{block_id}"},
                    ]
                ]
            }
            if block_id
            else None,
        )

    def _build_task_due_soon_payload(self, notification: NotificationModel) -> TelegramDispatchPayload:
        metadata = notification.metadata_json or {}
        task_title = metadata.get("task_title") or notification.title or "Task due soon"
        due_text = self._format_due(metadata.get("due_at"), metadata.get("timezone"))
        task_id = notification.task_id or str(metadata.get("task_id") or "")
        return TelegramDispatchPayload(
            text="\n".join(
                line
                for line in (
                    f"Due soon: {task_title}",
                    due_text,
                    notification.body.strip(),
                )
                if line
            ),
            reply_markup={
                "inline_keyboard": [
                    [
                        {"text": "Done", "callback_data": f"task:done:{task_id}"},
                    ]
                ]
            }
            if task_id
            else None,
        )

    def _build_fatigue_prompt_payload(self, notification: NotificationModel) -> TelegramDispatchPayload:
        prompt = notification.title or "Quick fatigue check"
        return TelegramDispatchPayload(
            text="\n".join(line for line in (prompt, notification.body.strip()) if line),
            reply_markup={
                "inline_keyboard": [
                    [{"text": str(score), "callback_data": f"fatigue:score:{score}"} for score in range(0, 3)],
                    [{"text": str(score), "callback_data": f"fatigue:score:{score}"} for score in range(3, 6)],
                ]
            },
        )

    def _format_when(self, value: Any, timezone_name: Any) -> str | None:
        if not value:
            return None
        parsed = self._coerce_datetime(value)
        if parsed is None:
            return None
        zone = self._resolve_timezone(timezone_name)
        local_value = parsed.astimezone(zone) if zone is not None else parsed
        return f"When: {local_value.strftime('%a %b %d, %I:%M %p %Z')}"

    def _format_due(self, value: Any, timezone_name: Any) -> str | None:
        if not value:
            return None
        parsed = self._coerce_datetime(value)
        if parsed is None:
            return None
        zone = self._resolve_timezone(timezone_name)
        local_value = parsed.astimezone(zone) if zone is not None else parsed
        return f"Due: {local_value.strftime('%a %b %d, %I:%M %p %Z')}"

    def _coerce_datetime(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    def _resolve_timezone(self, name: Any) -> ZoneInfo | None:
        if not isinstance(name, str) or not name.strip():
            return None
        try:
            return ZoneInfo(name)
        except ZoneInfoNotFoundError:
            return None
