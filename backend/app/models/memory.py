from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class MemoryType(StrEnum):
    HABIT = "habit"
    PREFERENCE = "preference"
    PATTERN = "pattern"
    CONSTRAINT = "constraint"


class MemorySource(StrEnum):
    EXPLICIT = "explicit"
    BEHAVIOR = "behavior"
    INFERRED = "inferred"


@dataclass(slots=True)
class LearnedMemoryModel:
    id: str
    user_id: str
    memory_type: MemoryType
    domain: str
    statement: str
    source: MemorySource
    confidence: float
    last_confirmed_at: datetime | None
    metadata_json: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    is_active: bool = True

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "LearnedMemoryModel":
        embedding = record.get("embedding")
        if embedding is not None and not isinstance(embedding, list):
            embedding = list(embedding)
        return cls(
            id=str(record["id"]),
            user_id=str(record["user_id"]),
            memory_type=MemoryType(record["memory_type"]),
            domain=record.get("domain") or "planning",
            statement=record["statement"],
            source=MemorySource(record.get("source") or MemorySource.INFERRED.value),
            confidence=float(record.get("confidence") or 0.0),
            last_confirmed_at=record.get("last_confirmed_at"),
            metadata_json=record.get("metadata_json") or {},
            embedding=embedding,
            created_at=record.get("created_at"),
            updated_at=record.get("updated_at"),
            is_active=bool(record.get("is_active", True)),
        )
