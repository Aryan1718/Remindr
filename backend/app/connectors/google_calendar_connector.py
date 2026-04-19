from __future__ import annotations

import json
import ssl
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any
from urllib import error, parse, request

from fastapi import HTTPException, status


@lru_cache(maxsize=1)
def _build_ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


class GoogleCalendarConnector:
    base_url = "https://www.googleapis.com/calendar/v3"

    def fetch_events(
        self,
        *,
        access_token: str,
        calendar_id: str,
        time_min: datetime,
        time_max: datetime,
    ) -> list[dict[str, Any]]:
        query = parse.urlencode(
            {
                "singleEvents": "true",
                "orderBy": "startTime",
                "timeMin": self._format_datetime(time_min),
                "timeMax": self._format_datetime(time_max),
            }
        )
        encoded_calendar_id = parse.quote(calendar_id, safe="")
        url = f"{self.base_url}/calendars/{encoded_calendar_id}/events?{query}"
        req = request.Request(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with request.urlopen(req, timeout=15, context=_build_ssl_context()) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Google Calendar API error: {detail or exc.reason}",
            ) from exc
        except error.URLError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google Calendar API is unavailable",
            ) from exc

        events: list[dict[str, Any]] = []
        for item in payload.get("items") or []:
            if isinstance(item, dict):
                events.append({**item, "_calendar_id": calendar_id})
        return events

    def _format_datetime(self, value: datetime) -> str:
        normalized = value.astimezone(UTC)
        return normalized.isoformat().replace("+00:00", "Z")
