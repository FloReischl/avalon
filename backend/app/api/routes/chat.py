"""Text-chat streaming endpoint."""

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.schemas import ChatRequest
from app.commands.factory import build_command_registry
from app.persistence.chat_repository import ChatRepository
from app.persistence.authorization_repository import AuthorizationRepository
from app.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from app.runtime.ollama import OllamaRuntime
from app.services.chat import (
    ChatCompressionFailedError,
    ChatNotFoundError,
    ChatService,
    ChatTurn,
)
from app.mcp.client import HttpMcpToolClient
from app.services.tool_runner import ToolRunner
from app.state import get_avalon_state
from app.state import get_audio_call_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_service():
    """Create the text-chat service for one request."""
    engine = create_database_engine()
    repository = ChatRepository(create_session_factory(engine))

    try:
        state = get_avalon_state()
        tool_runner = (
            ToolRunner(OllamaRuntime(), HttpMcpToolClient)
            if state.current_llm.tool_support
            else None
        )
        yield ChatService(
            OllamaRuntime(),
            repository,
            state.current_avatar,
            build_command_registry(state, repository),
            tool_runner=tool_runner,
            agents=state.agents,

        )
    finally:
        engine.dispose()


def format_sse_event(event: str, data: dict[str, str]) -> str:
    """Format one Avalon server-sent event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def stream_chat_response(
    service: ChatService,
    turn: ChatTurn,
) -> AsyncIterator[str]:
    """Translate one persistent chat turn into the Avalon SSE protocol."""
    yield format_sse_event("chat", {"id": str(turn.chat_id)})

    response_text = ""
    try:
        async for chunk in service.stream_response(turn):
            response_text += chunk
            yield format_sse_event("chunk", {"text": chunk})
    except Exception as exc:
        logger.error("[chat] response stream failed: %s", exc)
        service.persist_stream_error(turn, exc)
        yield format_sse_event("error", {"message": str(exc) or exc.__class__.__name__})
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
    """Persist and stream one text-chat turn as Avalon SSE events."""
    try:
        message = request.message.strip()
        turn = service.start_turn(request.chat_id, message)
    except ChatNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ChatCompressionFailedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    call_status = get_audio_call_state().get_status()
    if call_status.active and call_status.chat_id == turn.chat_id:
        get_audio_call_state().set_turn_active(True)

    return StreamingResponse(
        stream_chat_response(service, turn),
        media_type="text/event-stream",
    )
