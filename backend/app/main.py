from fastapi import FastAPI

from app.api import register_middleware
from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
    )

    register_middleware(app, settings)
    app.include_router(api_router, prefix=settings.api_prefix)

    return app


app = create_app()
