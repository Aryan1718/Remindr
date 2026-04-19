from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api import register_middleware
from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.schemas.common import ErrorResponse


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
    )

    register_middleware(app, settings)
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict):
            error_detail = exc.detail
        else:
            error_detail = {"code": "http_error", "message": str(exc.detail), "details": {}}
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(error=error_detail).model_dump(),
        )

    return app


app = create_app()
