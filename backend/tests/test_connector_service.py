from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.models.connector import ConnectorModel, ConnectorProvider, ConnectorStatus
from app.schemas.connector import ConnectorConnectRequest, ConnectorSyncRequest
from app.services.connector_service import ConnectorService


def _connector(
    *,
    connector_id: str = "connector-1",
    user_id: str = "user-1",
    provider: ConnectorProvider = ConnectorProvider.GOOGLE_CALENDAR,
    status: ConnectorStatus = ConnectorStatus.CONNECTED,
    account_email: str | None = "user@example.com",
    metadata_json: dict | None = None,
) -> ConnectorModel:
    now = datetime(2026, 4, 19, 10, 0, tzinfo=timezone.utc)
    return ConnectorModel(
        id=connector_id,
        user_id=user_id,
        provider=provider,
        status=status,
        account_email=account_email,
        access_token_encrypted="token",
        refresh_token_encrypted="refresh",
        token_expires_at=now,
        metadata_json=metadata_json or {},
        last_sync_at=None,
        created_at=now,
        updated_at=now,
    )


class ConnectorServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ConnectorService.__new__(ConnectorService)
        self.service.repository = MagicMock()
        self.service.enqueue_connector_sync = MagicMock()

    def test_connect_google_calendar_stores_connector_row(self) -> None:
        stored = _connector(metadata_json={"calendar_id": "primary"})
        self.service.repository.upsert_connector.return_value = stored

        result = self.service.connect_google_calendar(
            user_id="user-1",
            payload=ConnectorConnectRequest(
                account_email="user@example.com",
                access_token="access",
                refresh_token="refresh",
                metadata_json={"calendar_id": "primary"},
            ),
        )

        self.assertEqual(result.provider, ConnectorProvider.GOOGLE_CALENDAR)
        self.service.repository.upsert_connector.assert_called_once()
        call = self.service.repository.upsert_connector.call_args.kwargs
        self.assertEqual(call["user_id"], "user-1")
        self.assertEqual(call["provider"], ConnectorProvider.GOOGLE_CALENDAR)
        self.assertEqual(call["account_email"], "user@example.com")

    def test_trigger_sync_enqueues_job(self) -> None:
        connector = _connector()
        self.service.repository.get_connector.return_value = connector
        self.service.enqueue_connector_sync.return_value = type(
            "Job",
            (),
            {
                "job_id": "job-1",
                "job_type": "connector_sync",
                "job_status": "queued",
            },
        )()

        result = self.service.trigger_sync(
            user_id="user-1",
            connector_id="connector-1",
            payload=ConnectorSyncRequest(),
        )

        self.assertEqual(result.job_status, "queued")
        self.service.enqueue_connector_sync.assert_called_once()
        self.service.repository.update_connector_sync_state.assert_called_once()

    def test_owner_scoping_enforced_for_sync(self) -> None:
        self.service.repository.get_connector.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            self.service.trigger_sync(
                user_id="user-2",
                connector_id="connector-1",
                payload=ConnectorSyncRequest(),
            )

        self.assertEqual(ctx.exception.status_code, 404)
        self.service.enqueue_connector_sync.assert_not_called()


if __name__ == "__main__":
    unittest.main()
