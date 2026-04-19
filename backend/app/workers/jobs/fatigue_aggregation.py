from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import pvariance
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import psycopg
from psycopg.rows import dict_row

from app.models.fatigue import (
    FatigueCheckinModel,
    FatiguePatternModel,
    FatigueTimeBucket,
    FatigueTrendDirection,
)
from app.repositories.fatigue import FatigueRepository


def _resolve_timezone(name: str | None) -> ZoneInfo:
    candidate = name or "America/Los_Angeles"
    try:
        return ZoneInfo(candidate)
    except ZoneInfoNotFoundError:
        return ZoneInfo("America/Los_Angeles")


def _bucket_for_datetime(value: datetime) -> FatigueTimeBucket:
    hour = value.hour
    if 5 <= hour <= 11:
        return FatigueTimeBucket.MORNING
    if 12 <= hour <= 16:
        return FatigueTimeBucket.AFTERNOON
    if 17 <= hour <= 20:
        return FatigueTimeBucket.EVENING
    return FatigueTimeBucket.NIGHT


def compute_pattern_confidence(*, sample_count: int, variance: float) -> float:
    sample_component = min(sample_count / 8, 1.0) * 0.8
    variance_penalty = min(max(variance, 0.0) / 4.0, 1.0) * 0.3
    confidence = 0.15 + sample_component - variance_penalty
    return round(min(max(confidence, 0.1), 0.99), 3)


@dataclass(slots=True)
class FatigueAggregationWorker:
    repository: FatigueRepository

    def recompute_patterns(
        self,
        *,
        user_id: str | None = None,
        days_back: int = 90,
        as_of: datetime | None = None,
    ) -> list[FatiguePatternModel]:
        effective_now = as_of or datetime.now(UTC)
        since = effective_now - timedelta(days=days_back)
        checkins = self.repository.list_checkins_for_aggregation(user_id=user_id, since=since)
        if not checkins:
            return []

        timezone_cache: dict[str, ZoneInfo] = {}
        grouped: dict[tuple[str, int, FatigueTimeBucket], list[FatigueCheckinModel]] = defaultdict(list)

        for checkin in checkins:
            zone = timezone_cache.setdefault(
                checkin.user_id,
                _resolve_timezone(self.repository.get_user_timezone(user_id=checkin.user_id)),
            )
            local_dt = (checkin.created_at or effective_now).astimezone(zone)
            key = (checkin.user_id, local_dt.weekday(), _bucket_for_datetime(local_dt))
            grouped[key].append(checkin)

        pattern_rows: list[FatiguePatternModel] = []
        for (owner_id, weekday, time_bucket), bucket_checkins in grouped.items():
            scores = [item.score for item in bucket_checkins]
            variance = pvariance(scores) if len(scores) > 1 else 0.0
            avg = sum(scores) / len(scores)
            latest_signal = max(item.created_at for item in bucket_checkins if item.created_at is not None)

            pattern_rows.append(
                FatiguePatternModel(
                    user_id=owner_id,
                    weekday=weekday,
                    time_bucket=time_bucket,
                    avg_fatigue=round(avg, 2),
                    min_fatigue=float(min(scores)),
                    max_fatigue=float(max(scores)),
                    fatigue_variance=round(variance, 3),
                    sample_count=len(scores),
                    confidence=compute_pattern_confidence(sample_count=len(scores), variance=variance),
                    trend_direction=FatigueTrendDirection.STABLE,
                    last_signal_at=latest_signal,
                    last_computed_at=effective_now,
                    metadata_json={"aggregation_days_back": days_back},
                )
            )

        return self.repository.upsert_patterns(pattern_rows)


def recompute_fatigue_patterns_job(*, database_url: str, user_id: str | None, days_back: int) -> list[FatiguePatternModel]:
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        worker = FatigueAggregationWorker(FatigueRepository(connection))
        return worker.recompute_patterns(user_id=user_id, days_back=days_back)
