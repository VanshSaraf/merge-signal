from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    timestamp: datetime


@router.get("/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    settings: Settings = get_settings()

    return HealthResponse(
        status="ok",
        service=settings.project_name,
        environment=settings.environment,
        timestamp=datetime.now(UTC),
    )
