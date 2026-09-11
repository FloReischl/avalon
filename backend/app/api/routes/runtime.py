"""Local model runtime control endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Response, status

from app.runtime.ollama import OllamaRuntime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runtime", tags=["runtime"])


@router.post("/warm-up", status_code=status.HTTP_204_NO_CONTENT)
async def warm_up_runtime() -> Response:
    """Make the configured local model resident without creating chat state."""
    try:
        await OllamaRuntime().warm_up()
    except RuntimeError as exc:
        logger.exception("[runtime] model warm-up failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Runtime warm-up failed.",
        ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)