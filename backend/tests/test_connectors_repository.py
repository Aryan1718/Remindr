from __future__ import annotations

import unittest
from datetime import datetime, timezone

from app.repositories.connectors import ConnectorRepository


class _FakeCursor:
    def __init__(self) -> None:
        self.executemany_calls: list[tuple[str, list[tuple[object, ...]]]] = []

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def executemany(self, query: str, params: list[tuple[object, ...]]) -> None:
        self.executemany_calls.append((query, params))


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor
        self.commit_calls = 0

    def cursor(self) -> _FakeCursor:
        return self._cursor

    def commit(self) -> None:
        self.commit_calls += 1


class ConnectorRepositoryTests(unittest.TestCase):
    def test_upsert_avoids_duplicate_normalized_rows(self) -> None:
        cursor = _FakeCursor()
        repository = ConnectorRepository(_FakeConnection(cursor))  # type: ignore[arg-type]
        synced_at = datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc)

        count = repository.upsert_external_calendar_events(
            [
                {
                    "user_id": "user-1",
                    "connector_id": "connector-1",
                    "external_event_id": "event-1",
                    "calendar_id": "primary",
                    "title": "First title",
                    "description": None,
                    "location": None,
                    "starts_at": synced_at,
                    "ends_at": synced_at,
                    "is_all_day": False,
                    "status": "confirmed",
                    "raw_payload_json": {"id": "event-1"},
                    "last_synced_at": synced_at,
                },
                {
                    "user_id": "user-1",
                    "connector_id": "connector-1",
                    "external_event_id": "event-1",
                    "calendar_id": "primary",
                    "title": "Latest title",
                    "description": None,
                    "location": None,
                    "starts_at": synced_at,
                    "ends_at": synced_at,
                    "is_all_day": False,
                    "status": "confirmed",
                    "raw_payload_json": {"id": "event-1", "updated": True},
                    "last_synced_at": synced_at,
                },
            ]
        )

        self.assertEqual(count, 1)
        self.assertEqual(len(cursor.executemany_calls), 1)
        _, params = cursor.executemany_calls[0]
        self.assertEqual(len(params), 1)
        self.assertEqual(params[0][4], "Latest title")


if __name__ == "__main__":
    unittest.main()
