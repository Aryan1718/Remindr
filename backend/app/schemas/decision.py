from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


DecisionMode = Literal["exploratory", "guided", "decisive"]


class DecisionContextOverrides(BaseModel):
    time_available_minutes: int | None = Field(default=None, ge=0, le=720)


class DecisionQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    domain_hint: str | None = Field(default=None, max_length=100)
    fatigue_score: int | None = Field(default=None, ge=0, le=5)
    context_overrides: DecisionContextOverrides = Field(default_factory=DecisionContextOverrides)

    @field_validator("query", "domain_hint")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class DecisionNextBestActionRequest(BaseModel):
    fatigue_score: int | None = Field(default=None, ge=0, le=5)
    time_available_minutes: int | None = Field(default=None, ge=0, le=720)
    query: str | None = Field(default=None, max_length=500)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class DecisionPlanDayRequest(BaseModel):
    date: date_type | None = None
    fatigue_score: int | None = Field(default=None, ge=0, le=5)
    include_recommended_blocks: bool = True


class DecisionSuggestionRead(BaseModel):
    task_id: str | None = None
    title: str
    summary: str
    score: float
    estimated_minutes: int | None = None
    due_at: datetime | None = None


class DecisionSuggestedActionRead(BaseModel):
    action_type: str
    label: str
    payload: dict[str, Any] = Field(default_factory=dict)


class DecisionResponse(BaseModel):
    decision_id: str
    mode: DecisionMode
    primary_recommendation: DecisionSuggestionRead
    alternatives: list[DecisionSuggestionRead] = Field(default_factory=list)
    reasoning_summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    follow_up_questions: list[str] = Field(default_factory=list)
    suggested_actions: list[DecisionSuggestedActionRead] = Field(default_factory=list)


class DayPlanBlockRead(BaseModel):
    task_id: str | None = None
    title: str
    starts_at: datetime
    ends_at: datetime
    summary: str


class DayPlanResponse(BaseModel):
    decision_id: str
    date: date_type
    mode: DecisionMode
    summary: str
    recommendations: list[DecisionSuggestionRead] = Field(default_factory=list)
    recommended_blocks: list[DayPlanBlockRead] = Field(default_factory=list)
    suggested_actions: list[DecisionSuggestedActionRead] = Field(default_factory=list)


class DecisionEnvelope(BaseModel):
    success: bool = True
    data: DecisionResponse
    message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class DayPlanEnvelope(BaseModel):
    success: bool = True
    data: DayPlanResponse
    message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
