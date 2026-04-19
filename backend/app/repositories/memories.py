from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg import sql

from app.models.memory import LearnedMemoryModel, MemorySource, MemoryType

LEARNED_MEMORY_COLUMNS = """
    id,
    user_id,
    memory_type,
    domain,
    statement,
    source,
    confidence,
    last_confirmed_at,
    metadata_json,
    embedding,
    created_at,
    updated_at,
    is_active
"""


def normalize_memory_statement(statement: str) -> str:
    return re.sub(r"\s+", " ", statement.strip()).casefold()


def _vector_literal(values: Iterable[float]) -> str:
    return "[" + ",".join(f"{float(value):.12g}" for value in values) + "]"


class MemoryRepository:
    def __init__(self, connection: psycopg.Connection) -> None:
        self.connection = connection

    def create_memory(
        self,
        *,
        user_id: str,
        memory_type: MemoryType,
        domain: str,
        statement: str,
        source: MemorySource,
        confidence: float,
        last_confirmed_at: datetime | None,
        metadata_json: dict[str, Any] | None = None,
        embedding: list[float] | None = None,
        is_active: bool = True,
    ) -> LearnedMemoryModel:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                insert into learned_memories (
                    user_id,
                    memory_type,
                    domain,
                    statement,
                    source,
                    confidence,
                    last_confirmed_at,
                    metadata_json,
                    embedding,
                    is_active
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                returning {LEARNED_MEMORY_COLUMNS}
                """,
                (
                    user_id,
                    memory_type.value,
                    domain,
                    statement,
                    source.value,
                    round(confidence, 3),
                    last_confirmed_at,
                    json.dumps(metadata_json or {}),
                    embedding,
                    is_active,
                ),
            )
            record = cursor.fetchone()
        self.connection.commit()
        return LearnedMemoryModel.from_record(record)

    def update_memory(
        self,
        *,
        memory_id: str,
        user_id: str,
        values: dict[str, Any],
    ) -> LearnedMemoryModel | None:
        if not values:
            return self.get_memory(memory_id=memory_id, user_id=user_id)

        assignments: list[sql.Composed] = []
        params: list[Any] = []
        for column, value in values.items():
            if column == "metadata_json":
                assignments.append(sql.SQL("{} = %s::jsonb").format(sql.Identifier(column)))
                params.append(json.dumps(value))
                continue
            if isinstance(value, (MemoryType, MemorySource)):
                value = value.value
            assignments.append(sql.SQL("{} = %s").format(sql.Identifier(column)))
            params.append(value)

        assignments.append(sql.SQL("updated_at = now()"))
        params.extend([memory_id, user_id])

        query = sql.SQL(
            """
            update learned_memories
            set {assignments}
            where id = %s and user_id = %s
            returning {columns}
            """
        ).format(
            assignments=sql.SQL(", ").join(assignments),
            columns=sql.SQL(LEARNED_MEMORY_COLUMNS),
        )

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            record = cursor.fetchone()

        if record is None:
            self.connection.rollback()
            return None

        self.connection.commit()
        return LearnedMemoryModel.from_record(record)

    def get_memory(self, *, memory_id: str, user_id: str) -> LearnedMemoryModel | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                select {LEARNED_MEMORY_COLUMNS}
                from learned_memories
                where id = %s and user_id = %s
                limit 1
                """,
                (memory_id, user_id),
            )
            record = cursor.fetchone()
        return LearnedMemoryModel.from_record(record) if record else None

    def find_active_memories_for_user(
        self,
        *,
        user_id: str,
        domain: str | None = None,
        limit: int = 50,
    ) -> list[LearnedMemoryModel]:
        clauses = ["user_id = %s", "is_active = true"]
        params: list[Any] = [user_id]
        if domain is not None:
            clauses.append("domain = %s")
            params.append(domain)

        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                select {LEARNED_MEMORY_COLUMNS}
                from learned_memories
                where {" and ".join(clauses)}
                order by confidence desc, coalesce(last_confirmed_at, created_at) desc
                limit %s
                """,
                [*params, limit],
            )
            records = cursor.fetchall()
        return [LearnedMemoryModel.from_record(record) for record in records]

    def find_possible_duplicate_memory(
        self,
        *,
        user_id: str,
        domain: str,
        statement: str,
    ) -> LearnedMemoryModel | None:
        normalized = normalize_memory_statement(statement)
        for memory in self.find_active_memories_for_user(user_id=user_id, domain=domain, limit=100):
            candidate = normalize_memory_statement(memory.metadata_json.get("normalized_statement") or memory.statement)
            if candidate == normalized:
                return memory
        return None

    def list_recent_memories(self, *, user_id: str, limit: int = 20) -> list[LearnedMemoryModel]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                select {LEARNED_MEMORY_COLUMNS}
                from learned_memories
                where user_id = %s and is_active = true
                order by coalesce(last_confirmed_at, updated_at, created_at) desc
                limit %s
                """,
                (user_id, limit),
            )
            records = cursor.fetchall()
        return [LearnedMemoryModel.from_record(record) for record in records]

    def get_relevant_memories(
        self,
        *,
        user_id: str,
        query: str | None,
        domain: str | None = None,
        limit: int = 5,
        embedding: Iterable[float] | None = None,
    ) -> list[LearnedMemoryModel]:
        if embedding is not None:
            vector = list(embedding)
            if vector:
                rows = self._get_relevant_memories_by_embedding(
                    user_id=user_id,
                    domain=domain,
                    limit=limit,
                    embedding=vector,
                )
                if rows:
                    return rows

        memories = self.find_active_memories_for_user(user_id=user_id, domain=domain, limit=100)
        if not query:
            return memories[:limit]

        keywords = {token for token in re.findall(r"[a-z0-9]+", query.casefold()) if len(token) >= 3}

        def rank(memory: LearnedMemoryModel) -> tuple[float, float, float]:
            haystack = f"{memory.domain} {memory.statement} {json.dumps(memory.metadata_json, sort_keys=True)}".casefold()
            keyword_hits = sum(1 for token in keywords if token in haystack)
            recency_value = (
                (memory.last_confirmed_at or memory.updated_at or memory.created_at or datetime(1970, 1, 1, tzinfo=UTC))
                .astimezone(UTC)
                .timestamp()
            )
            return (float(keyword_hits), float(memory.confidence), recency_value)

        ranked = sorted(memories, key=rank, reverse=True)
        if keywords:
            ranked = [memory for memory in ranked if rank(memory)[0] > 0] or ranked
        return ranked[:limit]

    def _get_relevant_memories_by_embedding(
        self,
        *,
        user_id: str,
        domain: str | None,
        limit: int,
        embedding: list[float],
    ) -> list[LearnedMemoryModel]:
        clauses = ["user_id = %s", "is_active = true", "embedding is not null"]
        params: list[Any] = [user_id]
        if domain is not None:
            clauses.append("domain = %s")
            params.append(domain)

        vector_literal = _vector_literal(embedding)
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    select {LEARNED_MEMORY_COLUMNS}
                    from learned_memories
                    where {" and ".join(clauses)}
                    order by embedding <=> %s::vector asc,
                             confidence desc,
                             coalesce(last_confirmed_at, updated_at, created_at) desc
                    limit %s
                    """,
                    [*params, vector_literal, limit],
                )
                records = cursor.fetchall()
        except psycopg.Error:
            self.connection.rollback()
            return []
        return [LearnedMemoryModel.from_record(record) for record in records]
