from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import SessionDep
from app.schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/db", response_model=HealthResponse)
async def health_db(db: SessionDep) -> HealthResponse:
    await db.execute(text("SELECT 1"))
    return HealthResponse(status="ok")
