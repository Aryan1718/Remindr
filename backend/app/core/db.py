from collections.abc import Generator

import psycopg
from psycopg.rows import dict_row

from app.core.config import get_settings


def get_database_url() -> str:
    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    return database_url


def get_db_connection() -> Generator[psycopg.Connection, None, None]:
    connection = psycopg.connect(get_database_url(), row_factory=dict_row)
    try:
        yield connection
    finally:
        connection.close()
