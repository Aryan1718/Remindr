from fastapi import APIRouter

from app.schemas.common import SuccessResponse

router = APIRouter()


@router.get("/health", response_model=SuccessResponse[dict[str, str]])
async def health_check() -> SuccessResponse[dict[str, str]]:
    return SuccessResponse(data={"status": "ok", "service": "backend"})
