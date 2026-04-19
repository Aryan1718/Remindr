from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.models.connector import ConnectorModel, ConnectorProvider, ConnectorStatus


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class ConnectorConnectRequest(BaseModel):
    account_email: str | None = Field(default=None, max_length=320)
    access_token: str | None = Field(default=None, min_length=1, max_length=4096)
    refresh_token: str | None = Field(default=None, min_length=1, max_length=4096)
    token_expires_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("account_email", "access_token", "refresh_token")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class ConnectorRead(BaseModel):
    id: str
    user_id: str
    provider: ConnectorProvider
    status: ConnectorStatus
    account_email: str | None
    metadata_json: dict[str, Any]
    last_sync_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_model(cls, connector: ConnectorModel) -> "ConnectorRead":
        return cls(
            id=connector.id,
            user_id=connector.user_id,
            provider=connector.provider,
            status=connector.status,
            account_email=connector.account_email,
            metadata_json=connector.metadata_json or {},
            last_sync_at=connector.last_sync_at,
            updated_at=connector.updated_at,
        )


class ConnectorSyncRequest(BaseModel):
    sync_mode: Literal["incremental", "full"] = "incremental"
    lookahead_days: int | None = Field(default=14, ge=1, le=60)
    lookback_days: int | None = Field(default=7, ge=0, le=30)
    force: bool = False


class ConnectorSyncTriggered(BaseModel):
    connector_id: str
    job_id: str
    job_type: str
    job_status: str


class ConnectorOAuthStartRead(BaseModel):
    authorization_url: str


class ConnectorListEnvelope(BaseModel):
    success: bool = True
    data: dict[str, Any]
    message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class ConnectorEnvelope(BaseModel):
    success: bool = True
    data: dict[str, Any]
    message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
