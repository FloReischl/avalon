"""Text-chat streaming endpoint."""

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.schemas import ChatRequest
from app.persistence.chat_repository import ChatRepository
from app.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from app.runtime.ollama import OllamaRuntime
from app.services.chat import ChatNotFoundError, ChatService, ChatTurn
from app.user_config import get_user_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_service():
    """Create the text-chat service for one request."""
    engine = create_database_engine()
    repository = ChatRepository(create_session_factory(engine))

    try:
        yield ChatService(
            OllamaRuntime(),
            repository,
            get_user_config().standard_avatar,
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

    try:
        async for chunk in service.stream_response(turn):
            yield format_sse_event("chunk", {"text": chunk})
    except RuntimeError:
        logger.exception("[chat] response stream failed")
        yield format_sse_event("error", {})
        return

    yield format_sse_event("done", {})
    await service.finalize_turn(turn)


@router.post("")
async def create_chat_response(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """Persist and stream one text-chat turn as Avalo SSE events."""
    try:
        turn = service.start_turn(request.chat_id, request.message)
    except ChatNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return StreamingResponse(
        stream_chat_response(service, turn),
        media_type="text/event-stream",
    )

