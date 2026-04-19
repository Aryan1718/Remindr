from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import psycopg
from psycopg.errors import UndefinedTable

from app.models.internal_calendar import CalendarBlockStatus, InternalCalendarBlockModel
from app.models.task import TaskModel
from app.models.user import UserModel, UserPreferencesModel
from app.repositories.internal_calendar import InternalCalendarRepository
from app.repositories.tasks import TaskRepository
from app.repositories.users import UserRepository
from app.schemas.decision import (
    DayPlanBlockRead,
    DayPlanResponse,
    DecisionContextOverrides,
    DecisionNextBestActionRequest,
    DecisionPlanDayRequest,
    DecisionQueryRequest,
    DecisionResponse,
    DecisionSuggestedActionRead,
    DecisionSuggestionRead,
)
from app.services.fatigue_service import FatigueService
from app.services.memory_service import MemoryService

logger = logging.getLogger("app.services.decision")


class _NoopMemoryService:
    def normalize_retrieval_query(self, *, query: str | None, domain: str | None = None) -> str | None:
        _ = domain
        return query

    def get_relevant_memories(
        self,
        user_id: str,
        query: str | None,
        domain: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, object]]:
        _ = (user_id, query, domain, limit)
        return []


@dataclass(slots=True)
class DecisionContext:
    user: UserModel | None
    preferences: UserPreferencesModel | None
    tasks: list[TaskModel]
    upcoming_blocks: list[InternalCalendarBlockModel]
    fatigue: DecisionFatigueState
    available_time_minutes: int
    relevant_memories: list[dict[str, object]]
    query: str | None = None
    domain_hint: str | None = None


@dataclass(slots=True)
class ScoredTask:
    task: TaskModel
    score: float
    urgency_score: float
    priority_score: float
    time_fit_score: float
    energy_fit_score: float
    planned_penalty: float
    deadline_risk_score: float
    reasons: list[str]


@dataclass(slots=True)
class DecisionFatigueState:
    score: int
    confidence: float
    source: str


class DecisionService:
    def __init__(
        self,
        connection: psycopg.Connection | None = None,
        *,
        task_repository: TaskRepository | None = None,
        calendar_repository: InternalCalendarRepository | None = None,
        user_repository: UserRepository | None = None,
        fatigue_service: FatigueService | None = None,
        memory_service: MemoryService | None = None,
    ) -> None:
        self.connection = connection
        self.task_repository = task_repository or self._require_repo(TaskRepository, connection)
        self.calendar_repository = calendar_repository or self._require_repo(InternalCalendarRepository, connection)
        self.user_repository = user_repository or self._require_repo(UserRepository, connection)
        self.fatigue_service = fatigue_service or FatigueService(connection)
        if memory_service is not None:
            self.memory_service = memory_service
        elif connection is not None:
            self.memory_service = MemoryService(connection)
        else:
            self.memory_service = _NoopMemoryService()

    def query(self, *, user_id: str, payload: DecisionQueryRequest) -> DecisionResponse:
        context = self.build_decision_context(
            user_id=user_id,
            query=payload.query,
            domain_hint=payload.domain_hint,
            fatigue_score=payload.fatigue_score,
            context_overrides=payload.context_overrides,
        )
        scored_tasks = self.score_tasks(context)
        response = self.format_decision_response(
            context=context,
            scored_tasks=scored_tasks,
            alternatives_limit=self._alternatives_limit(context.fatigue.score),
        )
        self._log_interaction_event(
            user_id=user_id,
            event_type="decision_query_answered",
            payload={
                "decision_id": response.decision_id,
                "query": payload.query,
                "mode": response.mode,
                "top_task_id": response.primary_recommendation.task_id,
            },
        )
        return response

    def next_best_action(self, *, user_id: str, payload: DecisionNextBestActionRequest) -> DecisionResponse:
        context = self.build_decision_context(
            user_id=user_id,
            query=payload.query or "What should I focus on next?",
            fatigue_score=payload.fatigue_score,
            context_overrides=DecisionContextOverrides(time_available_minutes=payload.time_available_minutes),
        )
        scored_tasks = self.score_tasks(context)
        response = self.format_decision_response(context=context, scored_tasks=scored_tasks, alternatives_limit=0)
        self._log_interaction_event(
            user_id=user_id,
            event_type="decision_next_best_action_answered",
            payload={
                "decision_id": response.decision_id,
                "mode": response.mode,
                "top_task_id": response.primary_recommendation.task_id,
            },
        )
        return response

    def plan_day(self, *, user_id: str, payload: DecisionPlanDayRequest) -> DayPlanResponse:
        context = self.build_decision_context(
            user_id=user_id,
            query="Plan my day",
            fatigue_score=payload.fatigue_score,
            context_overrides=DecisionContextOverrides(),
            target_date=payload.date,
        )
        scored_tasks = self.score_tasks(context)
        target_date = payload.date or self._now_in_user_timezone(context).date()
        recommendations = [self._to_suggestion(item) for item in scored_tasks[:3]]
        recommended_blocks = self._recommend_day_blocks(
            context=context,
            scored_tasks=scored_tasks[:3],
            target_date=target_date,
        ) if payload.include_recommended_blocks else []

        response = DayPlanResponse(
            decision_id=str(uuid4()),
            date=target_date,
            mode=self.select_mode_from_fatigue(context.fatigue.score),
            summary=self._build_plan_day_summary(recommendations, recommended_blocks, context),
            recommendations=recommendations,
            recommended_blocks=recommended_blocks,
            suggested_actions=self._suggest_actions(
                context=context,
                recommendation=recommendations[0] if recommendations else None,
            ),
        )
        self._log_interaction_event(
            user_id=user_id,
            event_type="decision_plan_day_answered",
            payload={
                "decision_id": response.decision_id,
                "date": response.date.isoformat(),
                "recommendation_count": len(recommendations),
            },
        )
        return response

    def build_decision_context(
        self,
        *,
        user_id: str,
        query: str | None = None,
        domain_hint: str | None = None,
        fatigue_score: int | None = None,
        context_overrides: DecisionContextOverrides | None = None,
        target_date: date | None = None,
    ) -> DecisionContext:
        user = self.user_repository.get_user(user_id)
        preferences = self.user_repository.get_preferences(user_id)
        timezone_name = user.timezone if user is not None else "UTC"
        now = self._now_in_timezone(timezone_name)

        tasks = self.task_repository.list_schedulable_tasks(user_id=user_id, limit=200)
        if target_date is None:
            upcoming_start = now
            upcoming_end = now + timedelta(days=7)
        else:
            day_start, day_end = self._day_bounds(target_date=target_date, timezone_name=timezone_name)
            upcoming_start = day_start
            upcoming_end = day_end + timedelta(hours=12)
        upcoming_blocks = self.calendar_repository.list_future_blocks(
            user_id=user_id,
            starts_after=upcoming_start,
            ends_before=upcoming_end,
            limit=200,
        )
        fatigue = self._resolve_fatigue(
            user_id=user_id,
            explicit_score=fatigue_score,
            timezone_name=timezone_name,
        )
        available_time = self._resolve_available_time_minutes(
            context_overrides=context_overrides,
            now=now,
            upcoming_blocks=upcoming_blocks,
        )

        return DecisionContext(
            user=user,
            preferences=preferences,
            tasks=tasks,
            upcoming_blocks=upcoming_blocks,
            fatigue=fatigue,
            available_time_minutes=available_time,
            relevant_memories=self._load_relevant_memories(user_id=user_id, query=query, domain_hint=domain_hint),
            query=query,
            domain_hint=domain_hint,
        )

    def score_tasks(self, context: DecisionContext) -> list[ScoredTask]:
        now = self._now_in_user_timezone(context)
        scheduled_soon_ids = {
            block.task_id
            for block in context.upcoming_blocks
            if block.task_id
            and block.status in {
                CalendarBlockStatus.SUGGESTED,
                CalendarBlockStatus.CONFIRMED,
                CalendarBlockStatus.RESCHEDULED,
            }
            and block.starts_at <= now + timedelta(hours=12)
        }

        scored: list[ScoredTask] = []
        for task in context.tasks:
            urgency = self._urgency_score(task, now)
            priority = float(task.priority * 1.8)
            time_fit = self._time_fit_score(task=task, available_minutes=context.available_time_minutes)
            energy_fit = self._energy_fit_score(task=task, fatigue_score=context.fatigue.score)
            planned_penalty = -4.0 if task.id in scheduled_soon_ids else 0.0
            deadline_risk = self._deadline_risk_score(task=task, now=now)
            memory_alignment = self._memory_alignment_score(task=task, context=context, now=now)
            total = urgency + priority + time_fit + energy_fit + planned_penalty + deadline_risk + memory_alignment
            reasons = self._build_task_reasons(
                task=task,
                urgency=urgency,
                time_fit=time_fit,
                energy_fit=energy_fit,
                planned_penalty=planned_penalty,
                deadline_risk=deadline_risk,
                memory_alignment=memory_alignment,
                context=context,
            )
            scored.append(
                ScoredTask(
                    task=task,
                    score=round(total, 2),
                    urgency_score=urgency,
                    priority_score=priority,
                    time_fit_score=time_fit,
                    energy_fit_score=energy_fit,
                    planned_penalty=planned_penalty,
                    deadline_risk_score=deadline_risk,
                    reasons=reasons,
                )
            )

        scored.sort(
            key=lambda item: (
                item.score,
                item.urgency_score,
                item.priority_score,
                -(item.task.estimated_minutes or 10_000),
            ),
            reverse=True,
        )
        return scored

    def select_mode_from_fatigue(self, fatigue_score: int) -> str:
        if fatigue_score <= 1:
            return "exploratory"
        if fatigue_score <= 3:
            return "guided"
        return "decisive"

    def format_decision_response(
        self,
        *,
        context: DecisionContext,
        scored_tasks: list[ScoredTask],
        alternatives_limit: int,
    ) -> DecisionResponse:
        if not scored_tasks:
            suggestion = DecisionSuggestionRead(
                title="No open work to push right now",
                summary="You do not have any pending, scheduled, or in-progress tasks. Use this slot to rest or capture new work.",
                score=0.0,
            )
            return DecisionResponse(
                decision_id=str(uuid4()),
                mode=self.select_mode_from_fatigue(context.fatigue.score),
                primary_recommendation=suggestion,
                alternatives=[],
                reasoning_summary="There are no active tasks in storage, so the engine cannot justify a work recommendation.",
                confidence=0.92,
                follow_up_questions=[],
                suggested_actions=self._suggest_actions(context=context, recommendation=None),
            )

        top = scored_tasks[0]
        confidence = self._confidence_for(top=top, context=context)
        follow_up = self._follow_up_questions(confidence=confidence, top=top, context=context)
        mode = self.select_mode_from_fatigue(context.fatigue.score)

        return DecisionResponse(
            decision_id=str(uuid4()),
            mode=mode,
            primary_recommendation=self._to_suggestion(top),
            alternatives=[self._to_suggestion(item) for item in scored_tasks[1 : 1 + alternatives_limit]],
            reasoning_summary=self._build_reasoning_summary(top=top, mode=mode),
            confidence=confidence,
            follow_up_questions=follow_up,
            suggested_actions=self._suggest_actions(context=context, recommendation=self._to_suggestion(top)),
        )

    def _require_repo(self, repo_cls: type, connection: psycopg.Connection | None) -> object:
        if connection is None:
            raise ValueError(f"{repo_cls.__name__} requires a database connection")
        return repo_cls(connection)

    def _resolve_available_time_minutes(
        self,
        *,
        context_overrides: DecisionContextOverrides | None,
        now: datetime,
        upcoming_blocks: list[InternalCalendarBlockModel],
    ) -> int:
        if context_overrides and context_overrides.time_available_minutes is not None:
            return context_overrides.time_available_minutes

        next_block = min((block for block in upcoming_blocks if block.starts_at > now), key=lambda block: block.starts_at, default=None)
        if next_block is None:
            return 90

        gap_minutes = int((next_block.starts_at - now).total_seconds() // 60)
        return max(15, min(gap_minutes, 90))

    def _urgency_score(self, task: TaskModel, now: datetime) -> float:
        if task.due_at is None:
            return 0.0

        hours_until_due = (task.due_at - now).total_seconds() / 3600
        if hours_until_due <= 0:
            return 12.0
        if hours_until_due <= 6:
            return 10.0
        if hours_until_due <= 24:
            return 8.0
        if hours_until_due <= 72:
            return 5.0
        if hours_until_due <= 168:
            return 3.0
        return 1.0

    def _time_fit_score(self, *, task: TaskModel, available_minutes: int) -> float:
        if task.estimated_minutes is None:
            return 1.0
        if task.estimated_minutes <= available_minutes:
            return 4.0
        if task.estimated_minutes <= max(available_minutes * 1.5, available_minutes + 15):
            return 1.5
        return -2.5

    def _energy_fit_score(self, *, task: TaskModel, fatigue_score: int) -> float:
        if task.energy_required is None:
            return 1.0

        capacity = max(1, 5 - fatigue_score)
        if task.energy_required <= capacity:
            return round(3.5 - abs(capacity - task.energy_required) * 0.4, 2)

        overload = task.energy_required - capacity
        return round(max(-5.0, 1.0 - overload * 3.0), 2)

    def _deadline_risk_score(self, *, task: TaskModel, now: datetime) -> float:
        if task.due_at is None or task.estimated_minutes is None:
            return 0.0

        minutes_until_due = max(0, (task.due_at - now).total_seconds() / 60)
        if minutes_until_due == 0:
            return 5.0
        if task.estimated_minutes >= minutes_until_due:
            return 5.0
        if task.estimated_minutes >= minutes_until_due * 0.5:
            return 2.5
        return 0.0

    def _build_task_reasons(
        self,
        *,
        task: TaskModel,
        urgency: float,
        time_fit: float,
        energy_fit: float,
        planned_penalty: float,
        deadline_risk: float,
        memory_alignment: float,
        context: DecisionContext,
    ) -> list[str]:
        reasons: list[str] = []
        if urgency >= 8:
            reasons.append("deadline is close")
        elif urgency >= 3:
            reasons.append("due date is coming up")

        if deadline_risk >= 2.5:
            reasons.append("delay raises deadline risk")

        if time_fit >= 4:
            reasons.append("fits the time you likely have")
        elif time_fit < 0:
            reasons.append("may not fit the current window")

        if energy_fit >= 2.5:
            reasons.append("matches your current bandwidth")
        elif energy_fit < 0:
            reasons.append("is energy-heavy for your current fatigue")

        if planned_penalty < 0:
            reasons.append("is already planned soon")

        reasons.extend(self._memory_reasons(task=task, context=context, memory_alignment=memory_alignment))

        if not reasons and task.priority >= 4:
            reasons.append("has high priority")
        return reasons

    def _build_reasoning_summary(self, *, top: ScoredTask, mode: str) -> str:
        reasons = ", ".join(top.reasons[:3]) if top.reasons else "it ranks highest across urgency, priority, and fit"
        if mode == "decisive":
            return f"Do `{top.task.title}` now because {reasons}."
        if mode == "guided":
            return f"`{top.task.title}` is the clearest next move because {reasons}."
        return f"`{top.task.title}` currently leads the list because {reasons}. The other options stay viable if your available time changes."

    def _confidence_for(self, *, top: ScoredTask, context: DecisionContext) -> float:
        confidence = 0.4
        if context.tasks:
            confidence += 0.15
        confidence += min(context.fatigue.confidence, 1.0) * 0.15
        if top.task.due_at is not None:
            confidence += 0.1
        if top.task.estimated_minutes is not None:
            confidence += 0.1
        if top.task.energy_required is not None:
            confidence += 0.1
        if top.score >= 12:
            confidence += 0.1
        return round(min(confidence, 0.95), 2)

    def _follow_up_questions(
        self,
        *,
        confidence: float,
        top: ScoredTask,
        context: DecisionContext,
    ) -> list[str]:
        if confidence >= 0.75:
            return []
        if top.task.estimated_minutes is None:
            return ["How much time do you realistically have right now?"]
        if context.fatigue.source == "pattern_estimate":
            return ["Quick check: does your fatigue feel closer to low, medium, or high right now?"]
        return ["Is there any hard constraint in the next hour that should change the recommendation?"]

    def _to_suggestion(self, item: ScoredTask) -> DecisionSuggestionRead:
        return DecisionSuggestionRead(
            task_id=item.task.id,
            title=item.task.title,
            summary=self._summarize_task_choice(item),
            score=item.score,
            estimated_minutes=item.task.estimated_minutes,
            due_at=item.task.due_at,
        )

    def _summarize_task_choice(self, item: ScoredTask) -> str:
        if item.reasons:
            return f"Best fit because {', '.join(item.reasons[:2])}."
        return "Best fit based on the current task ranking."

    def _suggest_actions(
        self,
        *,
        context: DecisionContext,
        recommendation: DecisionSuggestionRead | None,
    ) -> list[DecisionSuggestedActionRead]:
        actions: list[DecisionSuggestedActionRead] = []
        if recommendation and recommendation.task_id:
            duration = recommendation.estimated_minutes or min(context.available_time_minutes, 30)
            actions.append(
                DecisionSuggestedActionRead(
                    action_type="create_focus_block",
                    label="Create a focus block",
                    payload={"task_id": recommendation.task_id, "minutes": duration},
                )
            )

        if context.fatigue.source == "pattern_estimate" and context.preferences and context.preferences.fatigue_prompt_enabled:
            actions.append(
                DecisionSuggestedActionRead(
                    action_type="ask_fatigue_checkin",
                    label="Confirm fatigue level",
                    payload={},
                )
            )

        if recommendation and recommendation.due_at is not None and recommendation.task_id:
            actions.append(
                DecisionSuggestedActionRead(
                    action_type="schedule_reminder",
                    label="Schedule a reminder",
                    payload={"task_id": recommendation.task_id, "due_at": recommendation.due_at.isoformat()},
                )
            )
        return actions

    def _alternatives_limit(self, fatigue_score: int) -> int:
        mode = self.select_mode_from_fatigue(fatigue_score)
        if mode == "exploratory":
            return 3
        if mode == "guided":
            return 2
        return 0

    def _resolve_fatigue(
        self,
        *,
        user_id: str,
        explicit_score: int | None,
        timezone_name: str | None,
    ) -> DecisionFatigueState:
        if explicit_score is not None:
            return DecisionFatigueState(score=explicit_score, confidence=1.0, source="explicit")

        estimate = self.fatigue_service.estimate_current_fatigue(
            user_id=user_id,
            timezone_name=timezone_name,
        )
        source = "pattern_estimate"
        if estimate.explicit_checkin is not None and estimate.matched_pattern is not None:
            source = "blended"
        elif estimate.explicit_checkin is not None:
            source = "live_checkin"
        elif estimate.matched_pattern is not None:
            source = "historical_pattern"

        return DecisionFatigueState(
            score=max(0, min(5, int(round(estimate.estimated_fatigue_score)))),
            confidence=float(estimate.estimation_confidence),
            source=source,
        )

    def _recommend_day_blocks(
        self,
        *,
        context: DecisionContext,
        scored_tasks: list[ScoredTask],
        target_date: date,
    ) -> list[DayPlanBlockRead]:
        if not scored_tasks:
            return []

        timezone_name = context.user.timezone if context.user is not None else "UTC"
        day_start, day_end = self._day_bounds(target_date=target_date, timezone_name=timezone_name)
        day_blocks = [
            block for block in context.upcoming_blocks
            if block.starts_at < day_end and block.ends_at > day_start
        ]
        occupied_intervals = sorted((block.starts_at, block.ends_at) for block in day_blocks)
        cursor = day_start
        recommendations: list[DayPlanBlockRead] = []

        for candidate in scored_tasks:
            duration = timedelta(minutes=candidate.task.estimated_minutes or 30)
            for starts_at, ends_at in occupied_intervals:
                if cursor + duration <= starts_at:
                    break
                cursor = max(cursor, ends_at)
            if cursor + duration > day_end:
                break

            recommendations.append(
                DayPlanBlockRead(
                    task_id=candidate.task.id,
                    title=candidate.task.title,
                    starts_at=cursor,
                    ends_at=cursor + duration,
                    summary=self._summarize_task_choice(candidate),
                )
            )
            occupied_intervals.append((cursor, cursor + duration))
            occupied_intervals.sort(key=lambda interval: interval[0])
            cursor = cursor + duration + timedelta(minutes=15)

        return recommendations

    def _build_plan_day_summary(
        self,
        recommendations: list[DecisionSuggestionRead],
        blocks: list[DayPlanBlockRead],
        context: DecisionContext,
    ) -> str:
        if not recommendations:
            return "No active tasks are available, so the day plan stays intentionally light."

        top_titles = ", ".join(item.title for item in recommendations[:3])
        if blocks:
            return f"Prioritize {top_titles}. Recommended blocks are spaced around existing calendar commitments."
        if context.upcoming_blocks:
            return f"Prioritize {top_titles}. Existing calendar blocks leave limited room for new work blocks."
        return f"Prioritize {top_titles}. The calendar is open enough to place these as focus work."

    def _log_interaction_event(self, *, user_id: str, event_type: str, payload: dict[str, object]) -> None:
        if self.connection is None:
            return

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    insert into interaction_events (
                        user_id,
                        event_type,
                        entity_type,
                        payload_json
                    )
                    values (%s, %s, 'decision', %s::jsonb)
                    """,
                    (user_id, event_type, json.dumps(payload)),
                )
            self.connection.commit()
        except UndefinedTable:
            self.connection.rollback()
            logger.warning("interaction_events table not found; skipped %s event", event_type)

    def _load_relevant_memories(self, *, user_id: str, query: str | None, domain_hint: str | None) -> list[dict[str, object]]:
        normalized_query = self.memory_service.normalize_retrieval_query(query=query, domain=domain_hint)
        return self.memory_service.get_relevant_memories(
            user_id=user_id,
            query=normalized_query,
            domain=domain_hint,
            limit=5,
        )

    def _memory_alignment_score(self, *, task: TaskModel, context: DecisionContext, now: datetime) -> float:
        score = 0.0
        hour = now.hour
        evening_now = hour >= 17
        for memory in context.relevant_memories:
            statement = str(memory.get("statement") or "").casefold()
            confidence = float(memory.get("confidence") or 0.0)
            metadata = memory.get("metadata_json") or {}

            if "avoids demanding evening work" in statement and evening_now and (task.energy_required or 0) >= 4:
                score -= 1.5 * confidence
            if "shorter focus blocks" in statement:
                preferred_duration = int((metadata or {}).get("preferred_duration_minutes") or 45)
                if task.estimated_minutes is not None and task.estimated_minutes <= preferred_duration:
                    score += 1.1 * confidence
                elif task.estimated_minutes is not None and task.estimated_minutes >= 90:
                    score -= 1.0 * confidence
            if "morning is a better execution window than evening" in statement and evening_now:
                score -= 0.7 * confidence
            if "weaker execution window" in statement and evening_now and task.priority < 4:
                score -= 0.5 * confidence
        return round(score, 2)

    def _memory_reasons(
        self,
        *,
        task: TaskModel,
        context: DecisionContext,
        memory_alignment: float,
    ) -> list[str]:
        if not context.relevant_memories or memory_alignment == 0:
            return []
        reasons: list[str] = []
        for memory in context.relevant_memories:
            statement = str(memory.get("statement") or "").casefold()
            if "shorter focus blocks" in statement and task.estimated_minutes is not None and task.estimated_minutes <= 45:
                reasons.append("matches your usual preference for shorter focus blocks")
                break
            if "avoids demanding evening work" in statement and memory_alignment < 0:
                reasons.append("runs against your usual evening energy pattern")
                break
        return reasons

    def _now_in_user_timezone(self, context: DecisionContext) -> datetime:
        timezone_name = context.user.timezone if context.user is not None else "UTC"
        return self._now_in_timezone(timezone_name)

    def _now_in_timezone(self, timezone_name: str) -> datetime:
        try:
            return datetime.now(ZoneInfo(timezone_name))
        except ZoneInfoNotFoundError:
            return datetime.now(UTC)

    def _day_bounds(self, *, target_date: date, timezone_name: str) -> tuple[datetime, datetime]:
        try:
            tz = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            tz = UTC
        day_start = datetime.combine(target_date, time(hour=8), tzinfo=tz)
        day_end = datetime.combine(target_date, time(hour=20), tzinfo=tz)
        return day_start, day_end
