"""Text-chat streaming endpoint."""

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.schemas import ChatRequest
from app.commands.factory import build_command_registry
from app.persistence.chat_repository import ChatRepository
from app.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from app.runtime.ollama import OllamaRuntime
from app.services.chat import ChatNotFoundError, ChatService, ChatTurn
from app.state import get_avalo_state
from app.state import get_audio_call_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_service():
    """Create the text-chat service for one request."""
    engine = create_database_engine()
    repository = ChatRepository(create_session_factory(engine))

    try:
        state = get_avalo_state()

        yield ChatService(
            OllamaRuntime(),
            repository,
            state.current_avatar,
            build_command_registry(state),
        )
    finally:
        engine.dispose()


def format_sse_event(event: str, data: dict[str, str]) -> str:
    """Format one Avalo server-sent event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def stream_chat_response(
    service: ChatService,
    turn: ChatTurn,
) -> AsyncIterator[str]:
    """Translate one persistent chat turn into the Avalo SSE protocol."""
    yield format_sse_event("chat", {"id": str(turn.chat_id)})

    response_text = ""
    try:
        async for chunk in service.stream_response(turn):
            response_text += chunk
            yield format_sse_event("chunk", {"text": chunk})
    except RuntimeError:
        logger.exception("[chat] response stream failed")
        yield format_sse_event("error", {})
        return

    yield format_sse_event("done", {})
    await service.finalize_turn(turn)
    call_state = get_audio_call_state()
    status = call_state.get_status()
    if status.active and status.chat_id == turn.chat_id:
        call_state.queue_speech(response_text)


@router.post("")
async def create_chat_response(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """Persist and stream one text-chat turn as Avalo SSE events."""
    try:
        message = request.message.strip()
        turn = service.start_turn(request.chat_id, message)
    except ChatNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    call_status = get_audio_call_state().get_status()
    if call_status.active and call_status.chat_id == turn.chat_id:
        get_audio_call_state().set_turn_active(True)

    return StreamingResponse(
        stream_chat_response(service, turn),
        media_type="text/event-stream",
    )
