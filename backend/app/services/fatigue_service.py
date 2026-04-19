from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import psycopg

from app.models.fatigue import (
    FatigueEstimateModel,
    FatigueModeRecommendation,
    FatiguePatternModel,
    FatigueTimeBucket,
)
from app.repositories.fatigue import FatigueRepository
from app.schemas.fatigue import (
    FatigueCheckinCreateRequest,
    FatigueCheckinListFilters,
    FatigueCheckinRead,
    FatiguePatternFilters,
    FatiguePatternRead,
    FatiguePatternRecomputeJobRead,
    FatiguePatternRecomputeRequest,
)
from app.workers.scheduler import enqueue_fatigue_pattern_recompute

RECENT_CHECKIN_MAX_AGE = timedelta(hours=6)


def _resolve_timezone(name: str | None) -> ZoneInfo:
    candidate = name or "America/Los_Angeles"
    try:
        return ZoneInfo(candidate)
    except ZoneInfoNotFoundError:
        return ZoneInfo("America/Los_Angeles")


def bucket_for_datetime(value: datetime) -> FatigueTimeBucket:
    hour = value.hour
    if 5 <= hour <= 11:
        return FatigueTimeBucket.MORNING
    if 12 <= hour <= 16:
        return FatigueTimeBucket.AFTERNOON
    if 17 <= hour <= 20:
        return FatigueTimeBucket.EVENING
    return FatigueTimeBucket.NIGHT


def map_mode_for_score(score: float) -> FatigueModeRecommendation:
    rounded = round(score)
    if rounded <= 1:
        return FatigueModeRecommendation.EXPLORATORY
    if rounded <= 3:
        return FatigueModeRecommendation.GUIDED
    return FatigueModeRecommendation.DECISIVE


class FatigueService:
    def __init__(
        self,
        connection: psycopg.Connection | None,
        repository: FatigueRepository | None = None,
    ) -> None:
        self.repository = repository or FatigueRepository(connection)
        self.enqueue_fatigue_pattern_recompute = enqueue_fatigue_pattern_recompute

    def create_checkin(self, *, user_id: str, payload: FatigueCheckinCreateRequest) -> FatigueCheckinRead:
        checkin = self.repository.create_checkin(user_id=user_id, payload=payload)
        self.repository.log_event(
            user_id=user_id,
            event_type="fatigue_checkin_submitted",
            entity_id=checkin.id,
            payload={"score": checkin.score, "source": checkin.source},
        )
        self.enqueue_fatigue_pattern_recompute(
            user_id=user_id,
            days_back=90,
            mode="async",
        )
        return FatigueCheckinRead.from_model(checkin)

    def list_checkins(self, *, user_id: str, filters: FatigueCheckinListFilters) -> list[FatigueCheckinRead]:
        checkins = self.repository.list_checkins(user_id=user_id, limit=filters.limit)
        return [FatigueCheckinRead.from_model(checkin) for checkin in checkins]

    def list_patterns(self, *, user_id: str, filters: FatiguePatternFilters) -> list[FatiguePatternRead]:
        patterns = self.repository.list_patterns(user_id=user_id, filters=filters)
        return [FatiguePatternRead.from_model(pattern) for pattern in patterns]

    def recompute_patterns(
        self,
        *,
        user_id: str,
        payload: FatiguePatternRecomputeRequest,
        mode: str = "async",
    ) -> FatiguePatternRecomputeJobRead:
        job = enqueue_fatigue_pattern_recompute(user_id=user_id, days_back=payload.days_back, mode=mode)
        return FatiguePatternRecomputeJobRead(
            job_id=job.job_id,
            queue_name=job.queue_name,
            status=job.status,
            triggered_at=job.triggered_at,
            target_user_id=user_id,
            days_back=payload.days_back,
            mode=job.mode,
        )

    def estimate_current_fatigue(
        self,
        *,
        user_id: str,
        timezone_name: str | None = None,
        at: datetime | None = None,
    ) -> FatigueEstimateModel:
        effective_now = at or datetime.now(UTC)
        zone = _resolve_timezone(timezone_name or self.repository.get_user_timezone(user_id=user_id))
        local_dt = effective_now.astimezone(zone)
        time_bucket = bucket_for_datetime(local_dt)

        recent_checkin = self.repository.get_recent_checkin(
            user_id=user_id,
            since=effective_now - RECENT_CHECKIN_MAX_AGE,
        )
        pattern = self.repository.get_pattern(
            user_id=user_id,
            weekday=local_dt.weekday(),
            time_bucket=time_bucket,
        )

        score, pattern_confidence, estimation_confidence, source_mix, reasons = self._estimate_from_signals(
            recent_checkin=recent_checkin,
            pattern=pattern,
        )

        return FatigueEstimateModel(
            estimated_fatigue_score=score,
            time_bucket=time_bucket,
            pattern_confidence=pattern_confidence,
            estimation_confidence=estimation_confidence,
            mode_recommendation=map_mode_for_score(score),
            source_mix=source_mix,
            reasons=reasons,
            explicit_checkin=recent_checkin,
            matched_pattern=pattern,
        )

    def _estimate_from_signals(
        self,
        *,
        recent_checkin,
        pattern: FatiguePatternModel | None,
    ) -> tuple[float, float, float, dict[str, float], list[str]]:
        source_mix: dict[str, float] = {}
        reasons: list[str] = []

        if recent_checkin is not None:
            reasons.append("Using recent explicit fatigue check-in as strongest signal")
            source_mix["live_checkin"] = 0.6
            if pattern is not None:
                source_mix["historical_pattern"] = 0.4
                reasons.append("Blending matching historical fatigue pattern for the current bucket")
                score = (recent_checkin.score * 0.6) + (pattern.avg_fatigue * 0.4)
                pattern_confidence = pattern.confidence
                estimation_confidence = round(min(0.95, 0.65 + (pattern.confidence * 0.2)), 3)
            else:
                source_mix["live_checkin"] = 1.0
                score = float(recent_checkin.score)
                pattern_confidence = 0.0
                estimation_confidence = 0.82
                reasons.append("No matching historical pattern available; using explicit input directly")
        elif pattern is not None:
            source_mix["historical_pattern"] = 1.0
            reasons.append("No recent explicit check-in; falling back to historical fatigue pattern")
            score = pattern.avg_fatigue
            pattern_confidence = pattern.confidence
            estimation_confidence = round(max(0.25, min(pattern.confidence, 0.85)), 3)
        else:
            source_mix["fallback_default"] = 1.0
            reasons.append("No recent explicit check-in or historical pattern; using neutral fallback")
            score = 2.5
            pattern_confidence = 0.0
            estimation_confidence = 0.2

        return round(score, 2), round(pattern_confidence, 3), round(estimation_confidence, 3), source_mix, reasons
