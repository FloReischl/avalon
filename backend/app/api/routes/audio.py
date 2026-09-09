"""Backend-local push-to-talk control and response streaming."""

from collections.abc import AsyncIterator
import logging
import sys
import traceback
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from app.api.routes.chat import format_sse_event
from app.api.schemas import AudioResponseRequest
from app.audio.capture import CaptureError, PipeWireRecorder
from app.persistence.chat_repository import ChatRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.runtime.ollama import OllamaRuntime
from app.services.audio_chat import AudioChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audio", tags=["audio"])

_audio_engine = create_database_engine()
_audio_repository = ChatRepository(create_session_factory(_audio_engine))
_audio_chat_service = AudioChatService(
    PipeWireRecorder(),
    OllamaRuntime(),
    _audio_repository,
)


def get_audio_chat_service() -> AudioChatService:
    """Return the process-local audio service owning the active recorder."""
    return _audio_chat_service


@router.post("/recording/start", status_code=status.HTTP_204_NO_CONTENT)
async def start_audio_recording(
    service: AudioChatService = Depends(get_audio_chat_service),
) -> Response:
    """Start one backend-local microphone recording."""
    try:
        await service.start_recording()
    except CaptureError as exc:
        print(
            f"[audio] start recording failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=409, detail="Audio recording unavailable.") from exc
    except Exception as exc:
        print(
            f"[audio] unexpected start recording failure: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        traceback.print_exc(file=sys.stderr)
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/recording/abort", status_code=status.HTTP_204_NO_CONTENT)
async def abort_audio_recording(
    service: AudioChatService = Depends(get_audio_chat_service),
) -> Response:
    """Discard an active backend-local microphone recording."""
    await service.abort_recording()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def stream_audio_response(
    service: AudioChatService,
    messages: list[dict[str, str]],
    chat_id: int | None = None,
) -> AsyncIterator[str]:
    """Translate audio chat output into Avalo's SSE protocol."""
    assistant_failed = False

    try:
        async for event in service.stream_response_with_transcription(
            messages,
            chat_id,
        ):
            if event.kind == "chat":
                yield format_sse_event("chat", {"id": event.text})
            elif event.kind == "assistant":
                yield format_sse_event("chunk", {"text": event.text})
            elif event.kind == "transcript":
                yield format_sse_event(
                    "transcript_chunk",
                    {"text": event.text},
                )
            elif event.kind == "transcript_error":
                yield format_sse_event("transcript_error", {})
            elif event.kind == "assistant_error":
                assistant_failed = True
    except Exception:
        logger.exception("[audio] response stream failed")
        yield format_sse_event("error", {})
        return

    if assistant_failed:
        yield format_sse_event("error", {})
        return

    if assistant_failed:
        yield format_sse_event("error", {})
        return

    yield format_sse_event("done", {})


@router.post("/recording/stop")
async def stop_audio_recording(
    request: AudioResponseRequest,
    service: AudioChatService = Depends(get_audio_chat_service),
) -> StreamingResponse:
    """Stop capture and stream Gemma's response using prior chat context."""
    messages = [message.model_dump() for message in request.messages]
    return StreamingResponse(
        stream_audio_response(service, messages, request.chat_id),
        media_type="text/event-stream",
    )


async def stream_dialog_response(
    service: AudioChatService,
    messages: list[dict[str, str]],
    chat_id: int | None = None,
) -> AsyncIterator[str]:
    """Translate one automatic dialog turn into Avalo's SSE protocol."""
    assistant_failed = False

    try:
        async for event in service.stream_dialog_response_with_transcription(
            messages,
            chat_id,
        ):
            if event.kind == "chat":
                yield format_sse_event("chat", {"id": event.text})
            elif event.kind == "assistant":
                yield format_sse_event("chunk", {"text": event.text})
            elif event.kind == "transcript":
                yield format_sse_event(
                    "transcript_chunk",
                    {"text": event.text},
                )
            elif event.kind == "transcript_error":
                yield format_sse_event("transcript_error", {})
            elif event.kind == "assistant_error":
                assistant_failed = True
    except Exception as exc:
        logger.exception("[audio-dialog] response stream failed")
        yield format_sse_event("error", {"message": str(exc)})
        return

    yield format_sse_event("done", {})


@router.post("/dialog/turn")
async def create_dialog_turn(
    request: AudioResponseRequest,
    service: AudioChatService = Depends(get_audio_chat_service),
) -> StreamingResponse:
    """Wait for one speech turn and stream Gemma's response."""
    messages = [message.model_dump() for message in request.messages]
    return StreamingResponse(
        stream_dialog_response(service, messages, request.chat_id),
        media_type="text/event-stream",
    )
