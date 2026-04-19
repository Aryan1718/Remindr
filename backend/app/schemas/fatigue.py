from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.fatigue import (
    FatigueCheckinModel,
    FatigueEstimateModel,
    FatigueModeRecommendation,
    FatiguePatternModel,
    FatigueTimeBucket,
    FatigueTrendDirection,
)


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class FatigueCheckinCreateRequest(BaseModel):
    score: int = Field(ge=0, le=5)
    source: str = Field(default="user", max_length=100)
    notes: str | None = Field(default=None, max_length=2000)
    context_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None

    @field_validator("source", "notes")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class FatigueCheckinListFilters(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)


class FatiguePatternFilters(BaseModel):
    weekday: int | None = Field(default=None, ge=0, le=6)
    time_bucket: FatigueTimeBucket | None = None
    limit: int = Field(default=100, ge=1, le=200)


class FatiguePatternRecomputeRequest(BaseModel):
    days_back: int = Field(default=90, ge=1, le=365)


class FatigueCheckinRead(BaseModel):
    id: str
    user_id: str
    score: int
    source: str
    notes: str | None
    context_json: dict[str, Any]
    created_at: datetime | None

    @classmethod
    def from_model(cls, checkin: FatigueCheckinModel) -> "FatigueCheckinRead":
        return cls(
            id=checkin.id,
            user_id=checkin.user_id,
            score=checkin.score,
            source=checkin.source,
            notes=checkin.notes,
            context_json=checkin.context_json,
            created_at=checkin.created_at,
        )


class FatiguePatternRead(BaseModel):
    id: str
    user_id: str
    weekday: int
    time_bucket: FatigueTimeBucket
    avg_fatigue: float
    min_fatigue: float
    max_fatigue: float
    fatigue_variance: float
    sample_count: int
    confidence: float
    trend_direction: FatigueTrendDirection
    last_signal_at: datetime | None
    last_computed_at: datetime | None
    metadata_json: dict[str, Any]

    @classmethod
    def from_model(cls, pattern: FatiguePatternModel) -> "FatiguePatternRead":
        return cls(
            id=pattern.id or "",
            user_id=pattern.user_id,
            weekday=pattern.weekday,
            time_bucket=pattern.time_bucket,
            avg_fatigue=pattern.avg_fatigue,
            min_fatigue=pattern.min_fatigue,
            max_fatigue=pattern.max_fatigue,
            fatigue_variance=pattern.fatigue_variance,
            sample_count=pattern.sample_count,
            confidence=pattern.confidence,
            trend_direction=pattern.trend_direction,
            last_signal_at=pattern.last_signal_at,
            last_computed_at=pattern.last_computed_at,
            metadata_json=pattern.metadata_json,
        )


class FatigueEstimateRead(BaseModel):
    estimated_fatigue_score: float
    time_bucket: FatigueTimeBucket
    pattern_confidence: float
    estimation_confidence: float
    mode_recommendation: FatigueModeRecommendation
    source_mix: dict[str, float]
    reasons: list[str]

    @classmethod
    def from_model(cls, estimate: FatigueEstimateModel) -> "FatigueEstimateRead":
        return cls(
            estimated_fatigue_score=estimate.estimated_fatigue_score,
            time_bucket=estimate.time_bucket,
            pattern_confidence=estimate.pattern_confidence,
            estimation_confidence=estimate.estimation_confidence,
            mode_recommendation=estimate.mode_recommendation,
            source_mix=estimate.source_mix,
            reasons=estimate.reasons,
        )


class FatigueCheckinResponseData(BaseModel):
    checkin: FatigueCheckinRead


class FatigueCheckinListResponseData(BaseModel):
    items: list[FatigueCheckinRead]


class FatiguePatternListResponseData(BaseModel):
    items: list[FatiguePatternRead]


class FatiguePatternRecomputeJobRead(BaseModel):
    job_id: str
    queue_name: str
    status: str
    triggered_at: datetime
    target_user_id: str
    days_back: int
    mode: str


class FatiguePatternRecomputeResponseData(BaseModel):
    job: FatiguePatternRecomputeJobRead
