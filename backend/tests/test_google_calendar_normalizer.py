from __future__ import annotations

import unittest
from datetime import datetime, timezone

from app.connectors.normalizers.google_calendar import normalize_google_calendar_event


class GoogleCalendarNormalizerTests(unittest.TestCase):
    def test_normalization_maps_timed_event(self) -> None:
        synced_at = datetime(2026, 4, 19, 9, 0, tzinfo=timezone.utc)
        event = normalize_google_calendar_event(
            user_id="user-1",
            connector_id="connector-1",
            raw_event={
                "id": "event-1",
                "_calendar_id": "primary",
                "summary": "Design review",
                "description": "Weekly sync",
                "location": "Room A",
                "status": "confirmed",
                "start": {"dateTime": "2026-04-20T09:00:00-07:00"},
                "end": {"dateTime": "2026-04-20T10:00:00-07:00"},
            },
            last_synced_at=synced_at,
        )

        self.assertEqual(event.external_event_id, "event-1")
        self.assertEqual(event.title, "Design review")
        self.assertFalse(event.is_all_day)
        self.assertEqual(event.starts_at.isoformat(), "2026-04-20T09:00:00-07:00")
        self.assertEqual(event.ends_at.isoformat(), "2026-04-20T10:00:00-07:00")

    def test_normalization_maps_all_day_event(self) -> None:
        synced_at = datetime(2026, 4, 19, 9, 0, tzinfo=timezone.utc)
        event = normalize_google_calendar_event(
            user_id="user-1",
            connector_id="connector-1",
            raw_event={
                "id": "event-2",
                "_calendar_id": "primary",
                "start": {"date": "2026-04-22"},
                "end": {"date": "2026-04-23"},
            },
            last_synced_at=synced_at,
        )

        self.assertEqual(event.title, "Untitled event")
        self.assertTrue(event.is_all_day)
        self.assertEqual(event.starts_at.isoformat(), "2026-04-22T00:00:00+00:00")
        self.assertEqual(event.ends_at.isoformat(), "2026-04-23T00:00:00+00:00")

    def test_malformed_payload_handling_is_safe(self) -> None:
        synced_at = datetime(2026, 4, 19, 9, 0, tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            normalize_google_calendar_event(
                user_id="user-1",
                connector_id="connector-1",
                raw_event={
                    "id": "broken",
                    "start": {"dateTime": "2026-04-22T10:00:00Z"},
                },
                last_synced_at=synced_at,
            )


if __name__ == "__main__":
    unittest.main()
