from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class FatigueTimeBucket(StrEnum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"


class FatigueTrendDirection(StrEnum):
    IMPROVING = "improving"
    WORSENING = "worsening"
    STABLE = "stable"
    UNKNOWN = "unknown"


class FatigueModeRecommendation(StrEnum):
    EXPLORATORY = "exploratory"
    GUIDED = "guided"
    DECISIVE = "decisive"


@dataclass(slots=True)
class FatigueCheckinModel:
    id: str
    user_id: str
    score: int
    source: str
    notes: str | None
    context_json: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "FatigueCheckinModel":
        return cls(
            id=str(record["id"]),
            user_id=str(record["user_id"]),
            score=int(record["score"]),
            source=record.get("source") or "user",
            notes=record.get("notes"),
            context_json=record.get("context_json") or {},
            created_at=record.get("created_at"),
        )


@dataclass(slots=True)
class FatiguePatternModel:
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
    metadata_json: dict[str, Any] = field(default_factory=dict)
    id: str | None = None

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "FatiguePatternModel":
        return cls(
            id=str(record["id"]),
            user_id=str(record["user_id"]),
            weekday=int(record["weekday"]),
            time_bucket=FatigueTimeBucket(record["time_bucket"]),
            avg_fatigue=float(record["avg_fatigue"]) if record.get("avg_fatigue") is not None else 0.0,
            min_fatigue=float(record["min_fatigue"]) if record.get("min_fatigue") is not None else 0.0,
            max_fatigue=float(record["max_fatigue"]) if record.get("max_fatigue") is not None else 0.0,
            fatigue_variance=float(record["fatigue_variance"]) if record.get("fatigue_variance") is not None else 0.0,
            sample_count=int(record.get("sample_count") or 0),
            confidence=float(record.get("confidence") or 0.0),
            trend_direction=FatigueTrendDirection(record.get("trend_direction") or FatigueTrendDirection.UNKNOWN.value),
            last_signal_at=record.get("last_signal_at"),
            last_computed_at=record.get("last_computed_at"),
            metadata_json=record.get("metadata_json") or {},
        )


@dataclass(slots=True)
class FatigueEstimateModel:
    estimated_fatigue_score: float
    time_bucket: FatigueTimeBucket
    pattern_confidence: float
    estimation_confidence: float
    mode_recommendation: FatigueModeRecommendation
    source_mix: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    explicit_checkin: FatigueCheckinModel | None = None
    matched_pattern: FatiguePatternModel | None = None
