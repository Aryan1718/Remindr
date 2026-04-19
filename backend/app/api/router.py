from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.decisions import router as decisions_router
from app.api.routes.connectors import router as connectors_router
from app.api.routes.fatigue import router as fatigue_router
from app.api.routes.health import router as health_router
from app.api.routes.internal_calendar import router as internal_calendar_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.users import router as users_router
from app.api.routes.telegram import router as telegram_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(connectors_router, tags=["connectors"])
api_router.include_router(internal_calendar_router, tags=["internal-calendar"])
api_router.include_router(tasks_router, tags=["tasks"])
api_router.include_router(fatigue_router, tags=["fatigue"])
api_router.include_router(decisions_router, tags=["decision"])
api_router.include_router(telegram_router, tags=["telegram"])
