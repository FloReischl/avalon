"""Local text-to-speech HTTP endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status


logger = logging.getLogger(__name__)


from app.api.schemas import TtsPlaybackEndedRequest, TtsRequest
from app.config import settings
from app.services.tts import TtsBusyError, TtsService
from app.tts.factory import create_tts_engine


PLAYBACK_ID_HEADER = "X-Avalo-TTS-Playback-ID"

router = APIRouter(prefix="/tts", tags=["tts"])

_tts_service = TtsService(
    create_tts_engine(),
    idle_unload_seconds=settings.tts_idle_unload_seconds,
)


def get_tts_service() -> TtsService:
    """Return the process-local TTS service."""
    return _tts_service


@router.post("")
async def synthesize_speech(
    request: TtsRequest,
    service: TtsService = Depends(get_tts_service),
) -> Response:
    """Synthesize plain text and return one complete WAV response."""
    try:
        result = await service.synthesize(request.text)
    except TtsBusyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Speech synthesis is already active.",
        ) from exc
    except ValueError as exc:
        logger.warning(
            "TTS request rejected: %s",
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TTS text is invalid.",
        ) from exc
    except RuntimeError as exc:
        logger.exception(
            "TTS synthesis failed."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Speech synthesis failed.",
        ) from exc

    return Response(
        content=result.audio,
        media_type="audio/wav",
        headers={
            PLAYBACK_ID_HEADER: result.playback_id,
        },
    )


@router.post(
    "/playback-ended",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def playback_ended(
    request: TtsPlaybackEndedRequest,
    service: TtsService = Depends(get_tts_service),
) -> Response:
    """Notify the backend that a frontend playback has stopped."""
    await service.playback_ended(request.playback_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
