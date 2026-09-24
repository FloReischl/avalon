"""Backend-local push-to-talk control and response streaming."""

import asyncio
from collections.abc import AsyncIterator
import logging

import sys
import traceback
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from app.api.routes.chat import format_sse_event
from app.api.schemas import (
    AudioCallStartRequest,
    AudioCallStatusResponse,
    AudioResponseRequest,
)
from app.audio.capture import CaptureError, PipeWireRecorder
from app.persistence.chat_repository import ChatRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.runtime.ollama import OllamaRuntime
from app.services.audio_text_chat import AudioTextChatService as AudioChatService

from app.services.audio_call import (
    AudioCallAlreadyActiveError,
    AudioCallState,
)
from app.state import get_audio_call_state, get_avalon_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audio", tags=["audio"])

_audio_engine = create_database_engine()
_audio_repository = ChatRepository(create_session_factory(_audio_engine))
_audio_chat_service = AudioChatService(
    PipeWireRecorder(),
    OllamaRuntime(),
    _audio_repository,
    lambda: get_avalon_state().current_avatar,
)


def get_audio_chat_service() -> AudioChatService:
    """Return the process-local audio service owning the active recorder."""
    return _audio_chat_service


@router.get("/call/status", response_model=AudioCallStatusResponse)
async def get_audio_call_status() -> AudioCallStatusResponse:
    """Return the global audio-call state for any frontend window."""
    return AudioCallStatusResponse(**get_audio_call_state().get_status().__dict__)


@router.post("/call/start", response_model=AudioCallStatusResponse)
async def start_audio_call(
    request: AudioCallStartRequest,
    service: AudioChatService = Depends(get_audio_chat_service),
) -> AudioCallStatusResponse:
    """Warm LLM and Whisper before publishing an active audio call."""
    if get_audio_call_state().get_status().active:
        raise HTTPException(status_code=409, detail="An audio call is already active.")

    try:
        await asyncio.gather(
            OllamaRuntime().warm_up(),
            service.warm_up_stt(),
        )
        status_value = get_audio_call_state().start(request.chat_id)
        await service.set_audio_call_active(True)
    except AudioCallAlreadyActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audio call unavailable.",
        ) from exc

    return AudioCallStatusResponse(**status_value.__dict__)


@router.post("/call/end", response_model=AudioCallStatusResponse)
async def end_audio_call(
    service: AudioChatService = Depends(get_audio_chat_service),
) -> AudioCallStatusResponse:
    """End the call and re-enable Whisper's idle lifecycle."""
    status_value = get_audio_call_state().end()
    await service.set_audio_call_active(False)
    return AudioCallStatusResponse(**status_value.__dict__)


@router.post("/call/turn/complete", response_model=AudioCallStatusResponse)
def complete_audio_call_turn() -> AudioCallStatusResponse:
    """Mark the active avatar call turn complete after local TTS playback."""
    if not get_audio_call_state().get_status().active:
        return AudioCallStatusResponse(**get_audio_call_state().get_status().__dict__)
    return AudioCallStatusResponse(
        **get_audio_call_state().set_turn_active(False).__dict__,
    )


@router.post("/call/speech/consume")
def consume_audio_call_speech() -> dict[str, str | None]:
    """Return and clear one assistant response reserved for avatar TTS."""
    return {"text": get_audio_call_state().consume_speech()}


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
    """Translate audio chat output into Avalon's SSE protocol."""
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
    except Exception:
        logger.exception("[audio] response stream failed")
        yield format_sse_event("error", {})
        return

    yield format_sse_event("done", {})


@router.post("/recording/stop")
async def stop_audio_recording(
    request: AudioResponseRequest,
    service: AudioChatService = Depends(get_audio_chat_service),
) -> StreamingResponse:
    """Stop capture and stream Gemma's response using prior chat context."""
    error_code = service.terminal_compression_error(request.chat_id)
    if error_code is not None:
        await service.abort_recording()
        raise HTTPException(status_code=409, detail=error_code)

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
    """Translate one automatic dialog turn into Avalon's SSE protocol."""
    try:
        async for event in service.stream_dialog_response_with_transcription(
            messages,
            chat_id,
        ):
            if event.kind == "processing":
                if get_audio_call_state().get_status().active:
                    get_audio_call_state().set_turn_active(True)
                yield format_sse_event("processing", {})
            elif event.kind == "chat":
                call_status = get_audio_call_state().get_status()
                if call_status.active and call_status.chat_id is None:
                    get_audio_call_state().bind_chat(int(event.text))
                yield format_sse_event("chat", {"id": event.text})
            elif event.kind == "assistant":
                yield format_sse_event("chunk", {"text": event.text})
            elif event.kind == "transcript":
                yield format_sse_event(
                    "transcript_chunk",
                    {"text": event.text},
                )
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
    error_code = service.terminal_compression_error(request.chat_id)
    if error_code is not None:
        raise HTTPException(status_code=409, detail=error_code)

    messages = [message.model_dump() for message in request.messages]
    return StreamingResponse(
        stream_dialog_response(service, messages, request.chat_id),
        media_type="text/event-stream",
    )
