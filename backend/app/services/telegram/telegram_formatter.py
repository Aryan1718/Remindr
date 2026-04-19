from __future__ import annotations

from app.schemas.decision import DayPlanResponse, DecisionResponse
from app.schemas.internal_calendar import InternalCalendarBlockRead
from app.schemas.task import TaskRead


def _clip_lines(lines: list[str], *, limit: int = 5) -> str:
    return "\n".join(line for line in lines if line.strip())[:2000] if len(lines) <= limit else "\n".join(
        line for line in lines[:limit] if line.strip()
    )


def format_task_created(task: TaskRead) -> str:
    lines = [f"Task saved:", task.title]
    if task.due_at is not None:
        lines.append(f"Due: {task.due_at.strftime('%b %d %I:%M %p')}")
    return _clip_lines(lines, limit=3)


def format_task_list(tasks: list[TaskRead]) -> str:
    if not tasks:
        return "No open tasks.\nCreate one so I can help prioritize it."

    lines = ["Open tasks:"]
    for task in tasks[:3]:
        due_text = f" - due {task.due_at.strftime('%b %d')}" if task.due_at is not None else ""
        lines.append(f"{task.title}{due_text}")
    return _clip_lines(lines, limit=4)


def format_next_action(response: DecisionResponse) -> str:
    lines = [
        "Best task right now:",
        response.primary_recommendation.title,
        f"Why: {response.primary_recommendation.summary}",
    ]
    if response.alternatives:
        lines.append(f"Alt: {response.alternatives[0].title}")
    return _clip_lines(lines, limit=4)


def format_plan_day(plan: DayPlanResponse) -> str:
    if not plan.recommendations:
        return _clip_lines([plan.summary], limit=2)

    lines = [
        "Plan for today:",
        plan.recommendations[0].title,
        f"Why: {plan.recommendations[0].summary}",
    ]
    if len(plan.recommendations) > 1:
        lines.append(f"Then: {plan.recommendations[1].title}")
    return _clip_lines(lines, limit=4)


def format_calendar_blocks(blocks: list[InternalCalendarBlockRead]) -> str:
    if not blocks:
        return "No upcoming calendar blocks.\nYour schedule looks open."

    lines = ["Next calendar blocks:"]
    for block in blocks[:3]:
        lines.append(f"{block.title} at {block.starts_at.strftime('%I:%M %p')}")
    return _clip_lines(lines, limit=4)


def format_general_decision(response: DecisionResponse) -> str:
    return _clip_lines(
        [
            response.primary_recommendation.title,
            response.primary_recommendation.summary,
            response.reasoning_summary,
        ],
        limit=4,
    )
