"""Database integration entry points live here when persistence is added."""

from app.core.config import get_settings


def get_database_url() -> str | None:
    return get_settings().database_url
