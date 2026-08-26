"""Backend health endpoint."""

from fastapi import APIRouter

from avalo_backend.api.schemas import HealthResponse
from avalo_backend.config import settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Report that the HTTP backend is ready."""

    return HealthResponse(service=settings.app_name)

