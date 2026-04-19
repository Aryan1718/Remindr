import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, computed_field

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    app_name: str = Field(default="Fatigue-Aware Personal Assistant Backend")
    environment: Literal["development", "staging", "production", "test"] = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    allowed_cors_origins: list[str] = Field(default_factory=list)
    database_url: str | None = None
    supabase_url: str | None = None
    supabase_jwt_secret: str | None = None
    supabase_jwt_issuer: str | None = None
    supabase_jwks_url: str | None = None
    supabase_jwt_audience: str | None = "authenticated"
    frontend_base_url: str | None = "http://localhost:5173"
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_oauth_redirect_uri: str | None = None
    google_oauth_scopes: str = (
        "openid https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/calendar.readonly"
    )
    connector_sync_eager: bool = True
    telegram_validate_bot_tokens: bool = False
    telegram_default_webhook_base_url: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resolved_supabase_jwt_issuer(self) -> str | None:
        if self.supabase_jwt_issuer:
            return self.supabase_jwt_issuer.rstrip("/")
        if self.supabase_url:
            return f"{self.supabase_url.rstrip('/')}/auth/v1"
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resolved_supabase_jwks_url(self) -> str | None:
        if self.supabase_jwks_url:
            return self.supabase_jwks_url
        issuer = self.resolved_supabase_jwt_issuer
        if issuer:
            return f"{issuer}/.well-known/jwks.json"
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resolved_frontend_base_url(self) -> str | None:
        if self.frontend_base_url:
            return self.frontend_base_url.rstrip("/")
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resolved_google_oauth_scopes(self) -> list[str]:
        raw_scopes = self.google_oauth_scopes.replace(",", " ")
        return [item.strip() for item in raw_scopes.split() if item.strip()]


def _parse_cors_origins(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


@lru_cache
def get_settings() -> Settings:
    env_values = {key.lower(): value for key, value in dotenv_values(ENV_FILE).items() if value is not None}
    runtime_env = {key.lower(): value for key, value in os.environ.items()}
    env_values.update(runtime_env)
    env_values["allowed_cors_origins"] = _parse_cors_origins(env_values.get("allowed_cors_origins"))
    if env_values.get("database_url") == "":
        env_values["database_url"] = None
    return Settings.model_validate(env_values)
