"""Backend-local push-to-talk control and response streaming."""

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from app.api.routes.chat import format_sse_event
from app.api.schemas import AudioResponseRequest
from app.audio.capture import CaptureError, PipeWireRecorder
from app.runtime.ollama import OllamaRuntime
from app.services.audio_chat import AudioChatService

router = APIRouter(prefix="/audio", tags=["audio"])

_audio_chat_service = AudioChatService(PipeWireRecorder(), OllamaRuntime())


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
        raise HTTPException(status_code=409, detail="Audio recording unavailable.") from exc
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
) -> AsyncIterator[str]:
    """Translate audio chat output into Avalo's SSE protocol."""
    try:
        async for chunk in service.stream_response(messages):
            yield format_sse_event("chunk", {"text": chunk})
    except (CaptureError, RuntimeError):
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
        stream_audio_response(service, messages),
        media_type="text/event-stream",
    )
