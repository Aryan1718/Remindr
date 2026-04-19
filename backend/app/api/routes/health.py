from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, object]:
    return {
        "success": True,
        "status": "ok",
        "service": "backend",
    }
