from collections.abc import Generator
from urllib.parse import urlparse

import psycopg
from fastapi import HTTPException, status
from psycopg.rows import dict_row

from app.core.config import get_settings


def get_database_url() -> str:
    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    return database_url


def connect_db(*, database_url: str | None = None) -> psycopg.Connection:
    return psycopg.connect(
        database_url or get_database_url(),
        row_factory=dict_row,
        prepare_threshold=None,
    )


def get_db_connection() -> Generator[psycopg.Connection, None, None]:
    database_url = get_database_url()
    parsed = urlparse(database_url)
    try:
        connection = connect_db(database_url=database_url)
    except psycopg.OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "database_unavailable",
                "message": "Database connection failed",
                "details": {
                    "host": parsed.hostname,
                    "port": parsed.port,
                    "database": parsed.path.lstrip("/") or None,
                    "driver_error": str(exc),
                },
            },
        ) from exc
    try:
        yield connection
    finally:
        connection.close()
