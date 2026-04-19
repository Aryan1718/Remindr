from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import ssl
from typing import Any

import jwt
import psycopg
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError, PyJWKClientError

from app.core.config import Settings, get_settings
from app.core.db import get_db_connection
from app.models.user import UserModel, UserPreferencesModel
from app.services.user_service import UserIdentity, UserService

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    auth_user_id: str
    email: str | None = None


def _unauthorized(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": code, "message": message, "details": {}},
        headers={"WWW-Authenticate": "Bearer"},
    )


@lru_cache(maxsize=1)
def _build_ssl_context() -> ssl.SSLContext:
    # Prefer the certifi CA bundle when available to avoid local certificate store issues.
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


@lru_cache(maxsize=1)
def _get_jwk_client(jwks_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_url, ssl_context=_build_ssl_context())


def _get_jwks_url(settings: Settings) -> str | None:
    return settings.resolved_supabase_jwks_url


def _decode_options(settings: Settings) -> dict[str, bool]:
    return {
        "verify_aud": settings.supabase_jwt_audience is not None,
        "verify_iss": settings.resolved_supabase_jwt_issuer is not None,
    }


def _decode_token(token: str, settings: Settings) -> dict:
    if settings.supabase_jwt_secret:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience=settings.supabase_jwt_audience,
            issuer=settings.resolved_supabase_jwt_issuer,
            options=_decode_options(settings),
        )

    jwks_url = _get_jwks_url(settings)
    if not jwks_url:
        raise RuntimeError("Supabase JWT verification is not configured")

    token_header = jwt.get_unverified_header(token)
    token_alg = token_header.get("alg")
    if not token_alg:
        raise InvalidTokenError("Token header is missing alg")

    signing_key = _get_jwk_client(jwks_url).get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=[token_alg],
        audience=settings.supabase_jwt_audience,
        issuer=settings.resolved_supabase_jwt_issuer,
        options=_decode_options(settings),
    )


def extract_identity_from_payload(payload: dict[str, Any]) -> UserIdentity:
    user_metadata = payload.get("user_metadata") or {}
    full_name = (
        user_metadata.get("full_name")
        or user_metadata.get("name")
        or payload.get("full_name")
        or payload.get("name")
    )
    return UserIdentity(
        auth_user_id=str(payload["sub"]),
        email=payload.get("email"),
        full_name=full_name,
    )


def get_current_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("missing_authorization", "Missing bearer token")

    try:
        claims = _decode_token(credentials.credentials, get_settings())
    except (InvalidTokenError, PyJWKClientError, RuntimeError) as exc:
        raise _unauthorized("invalid_token", "Invalid bearer token") from exc

    if not claims.get("sub"):
        raise _unauthorized("missing_sub", "Token is missing subject claim")
    return claims


def resolve_user_snapshot(
    *,
    payload: dict[str, Any],
    connection: psycopg.Connection,
    full_name_override: str | None = None,
    timezone_override: str | None = None,
) -> tuple[UserModel, UserPreferencesModel]:
    identity = extract_identity_from_payload(payload)
    return UserService(connection).get_or_create_user_snapshot(
        identity,
        full_name_override=full_name_override,
        timezone_override=timezone_override,
    )


def get_current_user_snapshot(
    payload: dict[str, Any] = Depends(get_current_token_payload),
    connection: psycopg.Connection = Depends(get_db_connection),
) -> tuple[UserModel, UserPreferencesModel]:
    return resolve_user_snapshot(
        payload=payload,
        connection=connection,
    )


def get_current_user(
    snapshot: tuple[UserModel, UserPreferencesModel] = Depends(get_current_user_snapshot),
) -> AuthenticatedUser:
    user, _ = snapshot
    return AuthenticatedUser(
        user_id=user.id,
        auth_user_id=user.auth_user_id,
        email=user.email,
    )


def get_current_user_id(user: AuthenticatedUser = Depends(get_current_user)) -> str:
    return user.user_id
