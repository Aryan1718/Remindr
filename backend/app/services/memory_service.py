from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import psycopg

from app.core.config import get_settings
from app.llm import get_llm_client
from app.llm.openai_compatible import OpenAICompatibleLLM
from app.models.fatigue import FatiguePatternModel, FatigueTimeBucket
from app.models.internal_calendar import FeedbackResponseType
from app.models.memory import LearnedMemoryModel, MemorySource, MemoryType
from app.repositories.fatigue import FatigueRepository
from app.repositories.internal_calendar import InternalCalendarRepository
from app.repositories.memories import MemoryRepository, normalize_memory_statement
from app.repositories.tasks import TaskRepository

MIN_MEMORY_EVIDENCE = 2
MIN_MEMORY_CONFIDENCE = 0.70
logger = logging.getLogger("app.services.memory")


class EmbeddingProvider(Protocol):
    def __call__(self, text: str) -> list[float]: ...


@dataclass(slots=True)
class MemoryCandidate:
    user_id: str
    memory_type: MemoryType
    domain: str
    statement: str
    source: MemorySource
    confidence: float
    last_confirmed_at: datetime | None
    metadata_json: dict[str, Any]


class MemoryService:
    def __init__(
        self,
        connection: psycopg.Connection | None = None,
        *,
        memory_repository: MemoryRepository | None = None,
        task_repository: TaskRepository | None = None,
        calendar_repository: InternalCalendarRepository | None = None,
        fatigue_repository: FatigueRepository | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.connection = connection
        self.memory_repository = memory_repository or self._require_repo(MemoryRepository, connection)
        self.task_repository = task_repository or self._require_repo(TaskRepository, connection)
        self.calendar_repository = calendar_repository or self._require_repo(InternalCalendarRepository, connection)
        self.fatigue_repository = fatigue_repository or self._require_repo(FatigueRepository, connection)
        self.embedding_provider = embedding_provider or self._build_default_embedding_provider()

    def upsert_memory(self, *, candidate: MemoryCandidate) -> LearnedMemoryModel | None:
        evidence_count = int(candidate.metadata_json.get("evidence_count") or 0)
        if evidence_count < MIN_MEMORY_EVIDENCE or candidate.confidence < MIN_MEMORY_CONFIDENCE:
            return None

        metadata = self._normalized_metadata(candidate.metadata_json, candidate.statement)
        duplicate = self.memory_repository.find_possible_duplicate_memory(
            user_id=candidate.user_id,
            domain=candidate.domain,
            statement=candidate.statement,
        )
        embedding = self._embed_statement(candidate.statement)

        if duplicate is None:
            return self.memory_repository.create_memory(
                user_id=candidate.user_id,
                memory_type=candidate.memory_type,
                domain=candidate.domain,
                statement=candidate.statement,
                source=candidate.source,
                confidence=candidate.confidence,
                last_confirmed_at=candidate.last_confirmed_at,
                metadata_json=metadata,
                embedding=embedding,
                is_active=True,
            )

        merged_metadata = self._merge_metadata(existing=duplicate.metadata_json, incoming=metadata)
        updated = self.memory_repository.update_memory(
            memory_id=duplicate.id,
            user_id=candidate.user_id,
            values={
                "memory_type": candidate.memory_type,
                "statement": candidate.statement,
                "source": candidate.source,
                "confidence": round(max(duplicate.confidence, candidate.confidence), 3),
                "last_confirmed_at": max(
                    [item for item in [duplicate.last_confirmed_at, candidate.last_confirmed_at] if item is not None],
                    default=duplicate.last_confirmed_at or candidate.last_confirmed_at,
                ),
                "metadata_json": merged_metadata,
                "embedding": embedding if embedding is not None else duplicate.embedding,
                "is_active": True,
            },
        )
        return updated

    def distill_memories_for_user(
        self,
        *,
        user_id: str,
        days_back: int = 45,
        as_of: datetime | None = None,
    ) -> list[LearnedMemoryModel]:
        effective_now = as_of or datetime.now(UTC)
        since = effective_now - timedelta(days=days_back)
        interaction_events = self.task_repository.list_recent_interaction_events(user_id=user_id, since=since, limit=300)
        calendar_feedback = self.calendar_repository.list_feedback_for_distillation(user_id=user_id, since=since, limit=300)
        fatigue_patterns = self.fatigue_repository.list_patterns_for_distillation(
            user_id=user_id,
            min_confidence=0.45,
            limit=50,
        )

        candidates = self.build_memory_candidates(
            user_id=user_id,
            interaction_events=interaction_events,
            calendar_feedback=calendar_feedback,
            fatigue_patterns=fatigue_patterns,
            as_of=effective_now,
        )
        persisted: list[LearnedMemoryModel] = []
        for candidate in candidates:
            stored = self.upsert_memory(candidate=candidate)
            if stored is not None:
                persisted.append(stored)
        return persisted

    def get_relevant_memories(
        self,
        user_id: str,
        query: str | None,
        domain: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        embedding = self._embed_statement(query) if query else None
        memories = self.memory_repository.get_relevant_memories(
            user_id=user_id,
            query=query,
            domain=domain,
            limit=limit,
            embedding=embedding,
        )
        return [
            {
                "id": memory.id,
                "domain": memory.domain,
                "statement": memory.statement,
                "memory_type": memory.memory_type.value,
                "source": memory.source.value,
                "confidence": memory.confidence,
                "metadata_json": memory.metadata_json,
            }
            for memory in memories
        ]

    def normalize_retrieval_query(self, *, query: str | None, domain: str | None = None) -> str | None:
        if query is None:
            return None
        cleaned = re.sub(r"\s+", " ", query.strip())
        if not cleaned:
            return None

        lowered = cleaned.casefold()
        if any(token in lowered for token in {"tonight", "evening", "night"}):
            lead = (
                "User is deciding whether to do cognitively demanding work tonight and needs timing guidance "
                "based on fatigue and learned behavior"
            )
        elif any(token in lowered for token in {"now", "right now", "start", "focus on next", "do first"}):
            lead = (
                "User wants to start a task now and needs guidance based on fatigue, timing preference, "
                "and task suitability"
            )
        elif any(token in lowered for token in {"plan", "schedule", "today", "day"}):
            lead = (
                "User wants planning guidance that should account for timing patterns, fatigue, and preferred work shape"
            )
        else:
            lead = (
                "User is asking for actionable guidance that should account for fatigue, timing preference, "
                "task suitability, and learned behavior"
            )

        if domain:
            lead = f"{lead} in the {domain} domain"
        return f"{lead}. Original request: {cleaned}"

    def build_memory_candidates(
        self,
        *,
        user_id: str,
        interaction_events: list[dict[str, Any]],
        calendar_feedback: list[dict[str, Any]],
        fatigue_patterns: list[FatiguePatternModel],
        as_of: datetime,
    ) -> list[MemoryCandidate]:
        candidates: list[MemoryCandidate] = []
        positive_responses = {
            FeedbackResponseType.ACCEPTED.value,
            FeedbackResponseType.COMPLETED.value,
        }
        negative_responses = {
            FeedbackResponseType.REJECTED.value,
            FeedbackResponseType.MOVED.value,
            FeedbackResponseType.SNOOZED.value,
            FeedbackResponseType.IGNORED.value,
        }

        high_fatigue_buckets = {
            pattern.time_bucket
            for pattern in fatigue_patterns
            if pattern.confidence >= 0.65 and pattern.avg_fatigue >= 3.5
        }

        for pattern in fatigue_patterns:
            if pattern.sample_count < 3 or pattern.confidence < 0.7:
                continue
            bucket_label = pattern.time_bucket.value
            if pattern.avg_fatigue >= 3.5:
                candidates.append(
                    self._build_candidate(
                        user_id=user_id,
                        memory_type=MemoryType.CONSTRAINT,
                        domain="planning",
                        statement=f"User often has high fatigue in the {bucket_label}",
                        evidence_count=pattern.sample_count,
                        contradiction_count=0,
                        supporting_event_types=["fatigue_patterns"],
                        supporting_reason_codes=[],
                        source_tables=["fatigue_patterns"],
                        recent_examples_count=pattern.sample_count,
                        time_bucket=bucket_label,
                        avg_fatigue=round(pattern.avg_fatigue, 2),
                        fatigue_pattern_confidence=pattern.confidence,
                        fatigue_sample_count=pattern.sample_count,
                        last_confirmed_at=pattern.last_signal_at or as_of,
                    )
                )
            elif pattern.avg_fatigue <= 2.0:
                candidates.append(
                    self._build_candidate(
                        user_id=user_id,
                        memory_type=MemoryType.PREFERENCE,
                        domain="planning",
                        statement=f"User usually has better energy in the {bucket_label}",
                        evidence_count=pattern.sample_count,
                        contradiction_count=0,
                        supporting_event_types=["fatigue_patterns"],
                        supporting_reason_codes=[],
                        source_tables=["fatigue_patterns"],
                        recent_examples_count=pattern.sample_count,
                        time_bucket=bucket_label,
                        avg_fatigue=round(pattern.avg_fatigue, 2),
                        fatigue_pattern_confidence=pattern.confidence,
                        fatigue_sample_count=pattern.sample_count,
                        last_confirmed_at=pattern.last_signal_at or as_of,
                    )
                )

        evening_support = 0
        evening_contradictions = 0
        evening_reason_codes: list[str] = []
        for row in calendar_feedback:
            bucket = self._time_bucket_for_row(row.get("starts_at") or row.get("created_at"))
            reason_code = (row.get("reason_code") or "").casefold()
            response_type = row.get("response_type")
            if bucket in {FatigueTimeBucket.EVENING, FatigueTimeBucket.NIGHT} and response_type in {
                FeedbackResponseType.REJECTED.value,
                FeedbackResponseType.MOVED.value,
            }:
                evening_support += 1
                if reason_code:
                    evening_reason_codes.append(reason_code)
            elif bucket in {FatigueTimeBucket.EVENING, FatigueTimeBucket.NIGHT} and response_type in positive_responses:
                evening_contradictions += 1
        if FatigueTimeBucket.EVENING in high_fatigue_buckets or FatigueTimeBucket.NIGHT in high_fatigue_buckets:
            evening_support += 1
        if evening_support >= MIN_MEMORY_EVIDENCE:
            candidates.append(
                self._build_candidate(
                    user_id=user_id,
                    memory_type=MemoryType.PATTERN,
                    domain="planning",
                    statement="User often avoids demanding evening work",
                    evidence_count=evening_support,
                    contradiction_count=evening_contradictions,
                    supporting_event_types=["calendar_feedback", "fatigue_patterns"],
                    supporting_reason_codes=evening_reason_codes,
                    source_tables=["calendar_feedback", "fatigue_patterns"],
                    recent_examples_count=evening_support,
                    time_bucket="evening",
                    last_confirmed_at=as_of,
                )
            )

        short_accepts = 0
        long_rejections = 0
        short_contradictions = 0
        for row in calendar_feedback:
            duration_minutes = int(row.get("duration_minutes") or 0)
            response_type = row.get("response_type")
            if 30 <= duration_minutes <= 45 and response_type in positive_responses:
                short_accepts += 1
            elif duration_minutes >= 90 and response_type in {
                FeedbackResponseType.REJECTED.value,
                FeedbackResponseType.MOVED.value,
            }:
                long_rejections += 1
            elif duration_minutes >= 90 and response_type in positive_responses:
                short_contradictions += 1
        block_size_support = short_accepts + long_rejections
        if block_size_support >= MIN_MEMORY_EVIDENCE:
            candidates.append(
                self._build_candidate(
                    user_id=user_id,
                    memory_type=MemoryType.PREFERENCE,
                    domain="planning",
                    statement="User prefers shorter focus blocks",
                    evidence_count=block_size_support,
                    contradiction_count=short_contradictions,
                    supporting_event_types=["calendar_feedback"],
                    supporting_reason_codes=[],
                    source_tables=["calendar_feedback"],
                    recent_examples_count=block_size_support,
                    preferred_duration_minutes=45,
                    last_confirmed_at=as_of,
                )
            )

        high_fatigue_accepts = 0
        high_fatigue_contradictions = 0
        for row in interaction_events:
            if row.get("event_type") not in {"suggestion_accepted", "suggestion_completed"}:
                continue
            fatigue_score = row.get("payload_json", {}).get("fatigue_score")
            if fatigue_score is not None and int(fatigue_score) >= 4:
                high_fatigue_accepts += 1
        for row in interaction_events:
            if row.get("event_type") in {"suggestion_rejected", "suggestion_ignored"}:
                fatigue_score = row.get("payload_json", {}).get("fatigue_score")
                if fatigue_score is not None and int(fatigue_score) >= 4:
                    high_fatigue_contradictions += 1
        if high_fatigue_accepts >= MIN_MEMORY_EVIDENCE:
            candidates.append(
                self._build_candidate(
                    user_id=user_id,
                    memory_type=MemoryType.PREFERENCE,
                    domain="guidance",
                    statement="User prefers direct suggestions when tired",
                    evidence_count=high_fatigue_accepts,
                    contradiction_count=high_fatigue_contradictions,
                    supporting_event_types=["interaction_events"],
                    supporting_reason_codes=[],
                    source_tables=["interaction_events"],
                    recent_examples_count=high_fatigue_accepts,
                    fatigue_threshold=4,
                    last_confirmed_at=as_of,
                )
            )

        morning_accepts = 0
        morning_contradictions = 0
        for row in calendar_feedback:
            bucket = self._time_bucket_for_row(row.get("starts_at") or row.get("created_at"))
            response_type = row.get("response_type")
            if bucket == FatigueTimeBucket.MORNING and response_type in positive_responses:
                morning_accepts += 1
            elif bucket == FatigueTimeBucket.MORNING and response_type in {
                FeedbackResponseType.REJECTED.value,
                FeedbackResponseType.MOVED.value,
            }:
                morning_contradictions += 1
        if morning_accepts >= MIN_MEMORY_EVIDENCE and evening_support >= MIN_MEMORY_EVIDENCE:
            combined_support = morning_accepts + evening_support
            candidates.append(
                self._build_candidate(
                    user_id=user_id,
                    memory_type=MemoryType.PATTERN,
                    domain="planning",
                    statement="Morning is a better execution window than evening",
                    evidence_count=combined_support,
                    contradiction_count=morning_contradictions + evening_contradictions,
                    supporting_event_types=["calendar_feedback", "fatigue_patterns"],
                    supporting_reason_codes=evening_reason_codes,
                    source_tables=["calendar_feedback", "fatigue_patterns"],
                    recent_examples_count=combined_support,
                    weekday="mixed",
                    last_confirmed_at=as_of,
                )
            )

        morning_focus_accepts = 0
        morning_focus_contradictions = 0
        morning_focus_types: list[str] = []
        for row in calendar_feedback:
            bucket = self._time_bucket_for_row(row.get("starts_at") or row.get("created_at"))
            response_type = row.get("response_type")
            block_type = (row.get("block_type") or "").casefold()
            if bucket != FatigueTimeBucket.MORNING or not self._is_focus_block(row):
                continue
            if response_type in positive_responses:
                morning_focus_accepts += 1
                if block_type:
                    morning_focus_types.append(block_type)
            elif response_type in negative_responses:
                morning_focus_contradictions += 1
        if morning_focus_accepts >= MIN_MEMORY_EVIDENCE:
            candidates.append(
                self._build_candidate(
                    user_id=user_id,
                    memory_type=MemoryType.PREFERENCE,
                    domain="planning",
                    statement="User usually accepts morning focus blocks",
                    evidence_count=morning_focus_accepts,
                    contradiction_count=morning_focus_contradictions,
                    supporting_event_types=["calendar_feedback"],
                    supporting_reason_codes=[],
                    source_tables=["calendar_feedback"],
                    recent_examples_count=morning_focus_accepts,
                    time_bucket="morning",
                    block_types=sorted(set(morning_focus_types)),
                    last_confirmed_at=as_of,
                )
            )

        evening_focus_moves = 0
        evening_focus_contradictions = 0
        evening_focus_reason_codes: list[str] = []
        for row in calendar_feedback:
            bucket = self._time_bucket_for_row(row.get("starts_at") or row.get("created_at"))
            response_type = row.get("response_type")
            reason_code = (row.get("reason_code") or "").casefold()
            if bucket not in {FatigueTimeBucket.EVENING, FatigueTimeBucket.NIGHT} or not self._is_focus_block(row):
                continue
            if response_type == FeedbackResponseType.MOVED.value:
                evening_focus_moves += 1
                if reason_code:
                    evening_focus_reason_codes.append(reason_code)
            elif response_type in positive_responses:
                evening_focus_contradictions += 1
        if evening_focus_moves >= MIN_MEMORY_EVIDENCE:
            candidates.append(
                self._build_candidate(
                    user_id=user_id,
                    memory_type=MemoryType.PATTERN,
                    domain="planning",
                    statement="User tends to move focus sessions out of the evening",
                    evidence_count=evening_focus_moves,
                    contradiction_count=evening_focus_contradictions,
                    supporting_event_types=["calendar_feedback"],
                    supporting_reason_codes=evening_focus_reason_codes,
                    source_tables=["calendar_feedback"],
                    recent_examples_count=evening_focus_moves,
                    time_bucket="evening",
                    last_confirmed_at=as_of,
                )
            )

        high_fatigue_rejections = 0
        high_fatigue_contradictions = 0
        fatigue_reason_codes: list[str] = []
        for row in calendar_feedback:
            fatigue_score = row.get("fatigue_score")
            response_type = row.get("response_type")
            if fatigue_score is None or int(fatigue_score) < 4:
                continue
            if response_type in {
                FeedbackResponseType.REJECTED.value,
                FeedbackResponseType.MOVED.value,
                FeedbackResponseType.SNOOZED.value,
            }:
                high_fatigue_rejections += 1
                reason_code = (row.get("reason_code") or "").casefold()
                if reason_code:
                    fatigue_reason_codes.append(reason_code)
            elif response_type in positive_responses:
                high_fatigue_contradictions += 1
        if high_fatigue_rejections >= MIN_MEMORY_EVIDENCE:
            candidates.append(
                self._build_candidate(
                    user_id=user_id,
                    memory_type=MemoryType.PATTERN,
                    domain="planning",
                    statement="User often rejects suggested blocks when fatigue is high",
                    evidence_count=high_fatigue_rejections,
                    contradiction_count=high_fatigue_contradictions,
                    supporting_event_types=["calendar_feedback"],
                    supporting_reason_codes=fatigue_reason_codes,
                    source_tables=["calendar_feedback"],
                    recent_examples_count=high_fatigue_rejections,
                    fatigue_threshold=4,
                    last_confirmed_at=as_of,
                )
            )

        night_short_support = 0
        night_short_contradictions = 0
        night_block_types: list[str] = []
        for row in calendar_feedback:
            bucket = self._time_bucket_for_row(row.get("starts_at") or row.get("created_at"))
            if bucket not in {FatigueTimeBucket.EVENING, FatigueTimeBucket.NIGHT}:
                continue
            duration_minutes = int(row.get("duration_minutes") or 0)
            response_type = row.get("response_type")
            block_type = (row.get("block_type") or "").casefold()
            if duration_minutes <= 45 and response_type in positive_responses:
                night_short_support += 1
                if block_type:
                    night_block_types.append(block_type)
            elif duration_minutes >= 75 and response_type in {
                FeedbackResponseType.REJECTED.value,
                FeedbackResponseType.MOVED.value,
                FeedbackResponseType.SNOOZED.value,
            }:
                night_short_support += 1
                if block_type:
                    night_block_types.append(block_type)
            elif (duration_minutes <= 45 and response_type in negative_responses) or (
                duration_minutes >= 75 and response_type in positive_responses
            ):
                night_short_contradictions += 1
        if night_short_support >= MIN_MEMORY_EVIDENCE:
            candidates.append(
                self._build_candidate(
                    user_id=user_id,
                    memory_type=MemoryType.PREFERENCE,
                    domain="planning",
                    statement="User prefers shorter work blocks at night",
                    evidence_count=night_short_support,
                    contradiction_count=night_short_contradictions,
                    supporting_event_types=["calendar_feedback"],
                    supporting_reason_codes=[],
                    source_tables=["calendar_feedback"],
                    recent_examples_count=night_short_support,
                    preferred_duration_minutes=45,
                    time_bucket="night",
                    block_types=sorted(set(night_block_types)),
                    last_confirmed_at=as_of,
                )
            )

        if evening_support >= MIN_MEMORY_EVIDENCE and (
            FatigueTimeBucket.EVENING in high_fatigue_buckets or FatigueTimeBucket.NIGHT in high_fatigue_buckets
        ):
            candidates.append(
                self._build_candidate(
                    user_id=user_id,
                    memory_type=MemoryType.CONSTRAINT,
                    domain="planning",
                    statement="Evening is a weaker execution window for this user",
                    evidence_count=evening_support,
                    contradiction_count=evening_contradictions,
                    supporting_event_types=["calendar_feedback", "fatigue_patterns"],
                    supporting_reason_codes=evening_reason_codes,
                    source_tables=["calendar_feedback", "fatigue_patterns"],
                    recent_examples_count=evening_support,
                    time_bucket="evening",
                    last_confirmed_at=as_of,
                )
            )

        return [candidate for candidate in candidates if candidate.confidence >= MIN_MEMORY_CONFIDENCE]

    def score_memory_candidate(
        self,
        *,
        evidence_count: int,
        contradiction_count: int,
        pattern_bonus: float = 0.0,
    ) -> float:
        total = max(evidence_count + contradiction_count, 1)
        consistency = evidence_count / total
        confidence = 0.35 + min(evidence_count, 5) * 0.12 + consistency * 0.18 + pattern_bonus - contradiction_count * 0.03
        return round(min(max(confidence, 0.05), 0.98), 3)

    def _build_candidate(
        self,
        *,
        user_id: str,
        memory_type: MemoryType,
        domain: str,
        statement: str,
        evidence_count: int,
        contradiction_count: int,
        supporting_event_types: list[str],
        supporting_reason_codes: list[str],
        source_tables: list[str],
        recent_examples_count: int,
        last_confirmed_at: datetime | None,
        **metadata: Any,
    ) -> MemoryCandidate:
        pattern_bonus = 0.04 if "fatigue_patterns" in source_tables else 0.0
        return MemoryCandidate(
            user_id=user_id,
            memory_type=memory_type,
            domain=domain,
            statement=statement,
            source=MemorySource.INFERRED,
            confidence=self.score_memory_candidate(
                evidence_count=evidence_count,
                contradiction_count=contradiction_count,
                pattern_bonus=pattern_bonus,
            ),
            last_confirmed_at=last_confirmed_at,
            metadata_json={
                "evidence_count": evidence_count,
                "supporting_event_types": supporting_event_types,
                "supporting_reason_codes": sorted({code for code in supporting_reason_codes if code}),
                "recent_examples_count": recent_examples_count,
                "contradiction_count": contradiction_count,
                "source_tables": sorted(set(source_tables)),
                **metadata,
            },
        )

    def _normalized_metadata(self, metadata: dict[str, Any], statement: str) -> dict[str, Any]:
        return {
            **metadata,
            "normalized_statement": normalize_memory_statement(statement),
        }

    def _merge_metadata(self, *, existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
        merged = {**existing, **incoming}
        merged["evidence_count"] = int(existing.get("evidence_count") or 0) + int(incoming.get("recent_examples_count") or 0)
        merged["recent_examples_count"] = max(
            int(existing.get("recent_examples_count") or 0),
            int(incoming.get("recent_examples_count") or 0),
        )
        merged["contradiction_count"] = max(
            int(existing.get("contradiction_count") or 0),
            int(incoming.get("contradiction_count") or 0),
        )
        merged["supporting_event_types"] = sorted(
            set(existing.get("supporting_event_types") or []).union(incoming.get("supporting_event_types") or [])
        )
        merged["supporting_reason_codes"] = sorted(
            set(existing.get("supporting_reason_codes") or []).union(incoming.get("supporting_reason_codes") or [])
        )
        merged["source_tables"] = sorted(set(existing.get("source_tables") or []).union(incoming.get("source_tables") or []))
        return merged

    def _time_bucket_for_row(self, value: datetime | None) -> FatigueTimeBucket | None:
        if value is None:
            return None
        hour = value.hour
        if 5 <= hour <= 11:
            return FatigueTimeBucket.MORNING
        if 12 <= hour <= 16:
            return FatigueTimeBucket.AFTERNOON
        if 17 <= hour <= 20:
            return FatigueTimeBucket.EVENING
        return FatigueTimeBucket.NIGHT

    def _is_focus_block(self, row: dict[str, Any]) -> bool:
        block_type = str(row.get("block_type") or "").casefold()
        title = str(row.get("title") or "").casefold()
        return block_type in {"focus_block", "suggested_task"} or title.startswith("focus")

    def _embed_statement(self, text: str | None) -> list[float] | None:
        if self.embedding_provider is None or not text:
            return None
        try:
            return self.embedding_provider(text)
        except Exception:
            logger.exception("memory embedding generation failed")
            return None

    def _build_default_embedding_provider(self) -> EmbeddingProvider | None:
        settings = get_settings()
        embedding_api_key = settings.resolved_openai_api_key
        model = settings.resolved_embedding_model
        base_url = settings.resolved_openai_base_url
        if not embedding_api_key or not model or not base_url:
            return None
        llm_client = OpenAICompatibleLLM(
            api_key=embedding_api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=settings.llm_timeout_seconds,
        )

        def provider(text: str) -> list[float]:
            embeddings = llm_client.generate_embeddings(texts=[text], model=model)
            if not embeddings or not embeddings[0]:
                raise ValueError("embedding provider returned no vector")
            return embeddings[0]

        return provider

    def _require_repo(self, repo_cls: type, connection: psycopg.Connection | None) -> object:
        if connection is None:
            raise ValueError(f"{repo_cls.__name__} requires a database connection")
        return repo_cls(connection)
