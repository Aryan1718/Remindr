from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import ssl
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any
from urllib import error, parse, request

import psycopg
from fastapi import HTTPException, status

from app.core.config import Settings, get_settings
from app.models.connector import ConnectorProvider, ConnectorStatus
from app.repositories.connectors import ConnectorRepository
from app.schemas.connector import (
    ConnectorConnectRequest,
    ConnectorOAuthStartRead,
    ConnectorRead,
    ConnectorSyncRequest,
    ConnectorSyncTriggered,
)
from app.workers.constants import DEFAULT_SYNC_LOOKAHEAD_DAYS, DEFAULT_SYNC_LOOKBACK_DAYS
from app.workers.rq import enqueue_connector_sync

logger = logging.getLogger("app.services.connector_service")


def _utcnow() -> datetime:
    return datetime.now(UTC)


@lru_cache(maxsize=1)
def _build_ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


class ConnectorService:
    def __init__(self, connection: psycopg.Connection, settings: Settings | None = None) -> None:
        self.repository = ConnectorRepository(connection)
        self.settings = settings or get_settings()
        self.enqueue_connector_sync = enqueue_connector_sync

    def list_connectors(self, *, user_id: str) -> list[ConnectorRead]:
        return [ConnectorRead.from_model(item) for item in self.repository.list_connectors(user_id=user_id)]

    def connect_google_calendar(
        self,
        *,
        user_id: str,
        payload: ConnectorConnectRequest,
    ) -> ConnectorRead:
        metadata = dict(payload.metadata_json)
        metadata.setdefault("calendar_id", "primary")
        metadata["connected_at"] = _utcnow().isoformat()

        connector = self.repository.upsert_connector(
            user_id=user_id,
            provider=ConnectorProvider.GOOGLE_CALENDAR,
            account_email=payload.account_email,
            access_token=payload.access_token,
            refresh_token=payload.refresh_token,
            token_expires_at=payload.token_expires_at,
            metadata=metadata,
            status=ConnectorStatus.CONNECTED,
        )
        return ConnectorRead.from_model(connector)

    def build_google_oauth_start(
        self,
        *,
        user_id: str,
        user_email: str | None = None,
    ) -> ConnectorOAuthStartRead:
        self._require_google_oauth_settings()
        state = self._generate_google_oauth_state(user_id=user_id)
        params = {
            "client_id": self.settings.google_client_id or "",
            "redirect_uri": self.settings.google_oauth_redirect_uri or "",
            "response_type": "code",
            "scope": " ".join(self.settings.resolved_google_oauth_scopes),
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state,
        }
        if user_email:
            params["login_hint"] = user_email

        return ConnectorOAuthStartRead(
            authorization_url=f"https://accounts.google.com/o/oauth2/v2/auth?{parse.urlencode(params)}"
        )

    def complete_google_oauth_callback(
        self,
        *,
        code: str,
        state: str,
    ) -> str:
        try:
            payload = self._parse_google_oauth_state(state)
            token_payload = self._exchange_google_oauth_code(code)
            profile = self._fetch_google_user_profile(token_payload["access_token"])
            token_expires_at = self._resolve_token_expires_at(token_payload.get("expires_in"))

            connector = self.connect_google_calendar(
                user_id=payload["user_id"],
                payload=ConnectorConnectRequest(
                    account_email=profile.get("email"),
                    access_token=token_payload["access_token"],
                    refresh_token=token_payload.get("refresh_token"),
                    token_expires_at=token_expires_at,
                    metadata_json={
                        "calendar_id": "primary",
                        "oauth_scope": token_payload.get("scope"),
                        "oauth_subject": profile.get("sub"),
                        "oauth_connected_via": "google_oauth",
                    },
                ),
            )
            sync = self.trigger_sync(
                user_id=payload["user_id"],
                connector_id=connector.id,
                payload=ConnectorSyncRequest(),
            )
            return self._build_frontend_callback_url(
                status_value="success",
                connector_id=connector.id,
                job_status=sync.job_status,
            )
        except HTTPException as exc:
            logger.warning("Google OAuth callback failed with HTTPException: %s", self._stringify_http_detail(exc.detail))
            return self._build_frontend_callback_url(
                status_value="error",
                reason=self._stringify_http_detail(exc.detail),
            )
        except Exception as exc:
            logger.exception("Google OAuth callback failed unexpectedly")
            return self._build_frontend_callback_url(
                status_value="error",
                reason=str(exc),
            )

    def trigger_sync(
        self,
        *,
        user_id: str,
        connector_id: str,
        payload: ConnectorSyncRequest,
    ) -> ConnectorSyncTriggered:
        connector = self.repository.get_connector(connector_id=connector_id, user_id=user_id)
        if connector is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")

        lookahead_days = payload.lookahead_days or DEFAULT_SYNC_LOOKAHEAD_DAYS
        lookback_days = payload.lookback_days or DEFAULT_SYNC_LOOKBACK_DAYS
        job = self.enqueue_connector_sync(
            connector_id=connector.id,
            user_id=user_id,
            lookahead_days=lookahead_days,
            lookback_days=lookback_days,
            force=payload.force,
        )

        metadata = dict(connector.metadata_json or {})
        metadata["sync_requested_at"] = _utcnow().isoformat()
        metadata["sync_requested_mode"] = payload.sync_mode
        self.repository.update_connector_sync_state(
            connector_id=connector.id,
            user_id=user_id,
            status=connector.status,
            metadata=metadata,
            last_sync_at=connector.last_sync_at,
        )

        return ConnectorSyncTriggered(
            connector_id=connector.id,
            job_id=job.job_id,
            job_type=job.job_type,
            job_status=job.job_status,
        )

    def _require_google_oauth_settings(self) -> None:
        if not self.settings.google_client_id or not self.settings.google_client_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google OAuth is not configured",
            )
        if not self.settings.google_oauth_redirect_uri:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google OAuth redirect URI is not configured",
            )
        if not self.settings.resolved_frontend_base_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Frontend base URL is not configured",
            )

    def _build_frontend_callback_url(
        self,
        *,
        status_value: str,
        connector_id: str | None = None,
        job_status: str | None = None,
        reason: str | None = None,
    ) -> str:
        self._require_google_oauth_settings()
        query = {"status": status_value}
        if connector_id:
            query["connector_id"] = connector_id
        if job_status:
            query["job_status"] = job_status
        if reason:
            query["reason"] = reason
        return f"{self.settings.resolved_frontend_base_url}/connectors/google-calendar/callback?{parse.urlencode(query)}"

    def _state_signing_key(self) -> bytes:
        self._require_google_oauth_settings()
        secret = self.settings.google_client_secret or self.settings.supabase_jwt_secret
        assert secret is not None
        return secret.encode("utf-8")

    def _generate_google_oauth_state(self, *, user_id: str) -> str:
        payload = {
            "user_id": user_id,
            "issued_at": int(_utcnow().timestamp()),
            "nonce": secrets.token_urlsafe(16),
        }
        encoded_payload = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")
        signature = hmac.new(
            self._state_signing_key(),
            encoded_payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        encoded_signature = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
        return f"{encoded_payload}.{encoded_signature}"

    def _parse_google_oauth_state(self, value: str) -> dict[str, Any]:
        try:
            encoded_payload, encoded_signature = value.split(".", 1)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state") from exc

        expected_signature = hmac.new(
            self._state_signing_key(),
            encoded_payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        actual_signature = base64.urlsafe_b64decode(self._restore_b64_padding(encoded_signature))
        if not hmac.compare_digest(expected_signature, actual_signature):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state verification failed")

        payload_bytes = base64.urlsafe_b64decode(self._restore_b64_padding(encoded_payload))
        payload = json.loads(payload_bytes.decode("utf-8"))
        issued_at = int(payload.get("issued_at") or 0)
        if issued_at <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state is malformed")
        if _utcnow() - datetime.fromtimestamp(issued_at, tz=UTC) > timedelta(minutes=10):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state has expired")
        if not payload.get("user_id"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state is missing user context")
        return payload

    def _exchange_google_oauth_code(self, code: str) -> dict[str, Any]:
        self._require_google_oauth_settings()
        body = parse.urlencode(
            {
                "code": code,
                "client_id": self.settings.google_client_id or "",
                "client_secret": self.settings.google_client_secret or "",
                "redirect_uri": self.settings.google_oauth_redirect_uri or "",
                "grant_type": "authorization_code",
            }
        ).encode("utf-8")
        req = request.Request(
            "https://oauth2.googleapis.com/token",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=15, context=_build_ssl_context()) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            logger.warning(
                "Google OAuth token exchange HTTPError status=%s body=%s",
                exc.code,
                detail,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Google OAuth token exchange failed: {detail or exc.reason}",
            ) from exc
        except error.URLError as exc:
            logger.warning(
                "Google OAuth token exchange URLError reason=%s type=%s",
                exc.reason,
                type(exc.reason).__name__,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Google OAuth token exchange is unavailable: {exc.reason}",
            ) from exc

        access_token = payload.get("access_token")
        if not access_token:
            logger.warning("Google OAuth response missing access token payload=%s", payload)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google OAuth response missing access token")
        return payload

    def _fetch_google_user_profile(self, access_token: str) -> dict[str, Any]:
        req = request.Request(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            method="GET",
        )
        try:
            with request.urlopen(req, timeout=10, context=_build_ssl_context()) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if isinstance(payload, dict):
                    return payload
        except Exception:
            return {}
        return {}

    def _resolve_token_expires_at(self, expires_in: Any) -> datetime | None:
        try:
            seconds = int(expires_in)
        except (TypeError, ValueError):
            return None
        return _utcnow() + timedelta(seconds=max(seconds, 0))

    def _restore_b64_padding(self, value: str) -> str:
        return value + "=" * (-len(value) % 4)

    def _stringify_http_detail(self, detail: Any) -> str:
        if isinstance(detail, str):
            return detail
        if isinstance(detail, dict):
            message = detail.get("message")
            if isinstance(message, str):
                return message
        return "Request failed"
