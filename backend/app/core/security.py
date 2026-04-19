from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import httpx
import jwt
import psycopg
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.db import get_db_connection

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    auth_user_id: str
    email: str | None = None


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=message,
    )


@lru_cache(maxsize=1)
def _get_jwk_client(jwks_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_url)


def _get_jwks_url(settings: Settings) -> str | None:
    if settings.supabase_jwks_url:
        return settings.supabase_jwks_url
    if settings.supabase_url:
        return f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    return None


def _decode_token(token: str, settings: Settings) -> dict:
    if settings.supabase_jwt_secret:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )

    jwks_url = _get_jwks_url(settings)
    if not jwks_url:
        raise RuntimeError("Supabase JWT verification is not configured")

    signing_key = _get_jwk_client(jwks_url).get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        options={"verify_aud": False},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    connection: psycopg.Connection = Depends(get_db_connection),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Missing bearer token")

    try:
        claims = _decode_token(credentials.credentials, get_settings())
    except (jwt.InvalidTokenError, httpx.HTTPError, RuntimeError) as exc:
        raise _unauthorized("Invalid bearer token") from exc

    auth_user_id = claims.get("sub")
    if not auth_user_id:
        raise _unauthorized("Token is missing subject claim")

    with connection.cursor() as cursor:
        cursor.execute(
            """
            select id, auth_user_id, email
            from users
            where auth_user_id = %s
            limit 1
            """,
            (auth_user_id,),
        )
        user = cursor.fetchone()

    if user is None:
        raise _forbidden("Authenticated user is not provisioned")

    return AuthenticatedUser(
        user_id=str(user["id"]),
        auth_user_id=str(user["auth_user_id"]),
        email=user.get("email"),
    )


def get_current_user_id(user: AuthenticatedUser = Depends(get_current_user)) -> str:
    return user.user_id
