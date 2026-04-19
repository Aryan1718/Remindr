from __future__ import annotations

from datetime import UTC, datetime, timedelta

import psycopg
from fastapi import HTTPException, status
from psycopg.rows import dict_row

from app.connectors.google_calendar_connector import GoogleCalendarConnector
from app.connectors.normalizers.google_calendar import normalize_google_calendar_event
from app.core.db import get_database_url
from app.models.connector import ConnectorProvider, ConnectorStatus
from app.repositories.connectors import ConnectorRepository
from app.workers.constants import DEFAULT_SYNC_LOOKAHEAD_DAYS, DEFAULT_SYNC_LOOKBACK_DAYS


def sync_connector_job(
    *,
    connector_id: str,
    user_id: str,
    lookahead_days: int = DEFAULT_SYNC_LOOKAHEAD_DAYS,
    lookback_days: int = DEFAULT_SYNC_LOOKBACK_DAYS,
    force: bool = False,
    connection: psycopg.Connection | None = None,
    google_connector: GoogleCalendarConnector | None = None,
    synced_at: datetime | None = None,
) -> dict[str, int | str]:
    owns_connection = connection is None
    connection = connection or psycopg.connect(get_database_url(), row_factory=dict_row)
    repository = ConnectorRepository(connection)
    google_connector = google_connector or GoogleCalendarConnector()
    synced_at = synced_at or datetime.now(UTC)

    try:
        connector = repository.get_connector(connector_id=connector_id, user_id=user_id)
        if connector is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")
        if connector.provider != ConnectorProvider.GOOGLE_CALENDAR:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported connector provider")
        if not connector.access_token_encrypted:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Connector access token is missing")

        window_start = synced_at - timedelta(days=lookback_days)
        window_end = synced_at + timedelta(days=lookahead_days)
        calendar_id = str((connector.metadata_json or {}).get("calendar_id") or "primary")
        raw_events = google_connector.fetch_events(
            access_token=connector.access_token_encrypted,
            calendar_id=calendar_id,
            time_min=window_start,
            time_max=window_end,
        )

        normalized_records: list[dict[str, object]] = []
        skipped_count = 0
        for raw_event in raw_events:
            try:
                normalized = normalize_google_calendar_event(
                    user_id=user_id,
                    connector_id=connector.id,
                    raw_event=raw_event,
                    last_synced_at=synced_at,
                )
            except ValueError:
                skipped_count += 1
                continue
            normalized_records.append(normalized.to_record())

        upserted_count = repository.upsert_external_calendar_events(normalized_records)
        metadata = dict(connector.metadata_json or {})
        metadata.update(
            {
                "calendar_id": calendar_id,
                "last_sync_force": force,
                "last_sync_window_start": window_start.isoformat(),
                "last_sync_window_end": window_end.isoformat(),
                "last_sync_event_count": upserted_count,
                "last_sync_skipped_count": skipped_count,
            }
        )
        repository.update_connector_sync_state(
            connector_id=connector.id,
            user_id=user_id,
            status=ConnectorStatus.CONNECTED,
            metadata=metadata,
            last_sync_at=synced_at,
        )
        repository.log_event(
            user_id=user_id,
            event_type="connector_synced",
            entity_id=connector.id,
            payload={
                "provider": connector.provider.value,
                "event_count": upserted_count,
                "skipped_count": skipped_count,
            },
        )
        return {
            "connector_id": connector.id,
            "provider": connector.provider.value,
            "event_count": upserted_count,
            "skipped_count": skipped_count,
        }
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise

        connector = repository.get_connector(connector_id=connector_id, user_id=user_id)
        if connector is not None:
            metadata = dict(connector.metadata_json or {})
            metadata["last_sync_error"] = str(exc)
            repository.update_connector_sync_state(
                connector_id=connector.id,
                user_id=user_id,
                status=ConnectorStatus.ERROR,
                metadata=metadata,
                last_sync_at=connector.last_sync_at,
            )
        raise
    finally:
        if owns_connection:
            connection.close()
