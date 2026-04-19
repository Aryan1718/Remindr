from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.models.connector import ConnectorProvider, ConnectorStatus
from app.workers.jobs.connector_sync import sync_connector_job


class _FakeGoogleConnector:
    def fetch_events(self, **_: object) -> list[dict[str, object]]:
        return [
            {
                "id": "event-1",
                "_calendar_id": "primary",
                "summary": "Standup",
                "status": "confirmed",
                "start": {"dateTime": "2026-04-20T09:00:00Z"},
                "end": {"dateTime": "2026-04-20T09:30:00Z"},
            },
            {
                "id": "broken",
                "_calendar_id": "primary",
                "start": {"dateTime": "2026-04-20T11:00:00Z"},
            },
        ]


class ConnectorSyncJobTests(unittest.TestCase):
    @patch("app.workers.jobs.connector_sync.ConnectorRepository")
    def test_sync_metadata_updates_after_successful_path(self, repository_cls: MagicMock) -> None:
        repository = repository_cls.return_value
        synced_at = datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc)
        connector = MagicMock(
            id="connector-1",
            user_id="user-1",
            provider=ConnectorProvider.GOOGLE_CALENDAR,
            status=ConnectorStatus.CONNECTED,
            access_token_encrypted="token",
            metadata_json={"calendar_id": "primary"},
            last_sync_at=None,
        )
        repository.get_connector.return_value = connector
        repository.upsert_external_calendar_events.return_value = 1

        result = sync_connector_job(
            connector_id="connector-1",
            user_id="user-1",
            connection=MagicMock(),
            google_connector=_FakeGoogleConnector(),
            synced_at=synced_at,
        )

        self.assertEqual(result["event_count"], 1)
        repository.upsert_external_calendar_events.assert_called_once()
        repository.update_connector_sync_state.assert_called_once()
        kwargs = repository.update_connector_sync_state.call_args.kwargs
        self.assertEqual(kwargs["status"], ConnectorStatus.CONNECTED)
        self.assertEqual(kwargs["last_sync_at"], synced_at)
        self.assertEqual(kwargs["metadata"]["last_sync_skipped_count"], 1)
        repository.log_event.assert_called_once()


if __name__ == "__main__":
    unittest.main()
