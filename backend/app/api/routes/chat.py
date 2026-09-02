"""Text-chat streaming endpoint."""

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.schemas import ChatRequest
from app.runtime.ollama import OllamaRuntime
from app.services.chat import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_service() -> ChatService:
    """Create the text-chat service for a request."""
    return ChatService(OllamaRuntime())


def format_sse_event(event: str, data: dict[str, str]) -> str:
    """Format one Avalo server-sent event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def stream_chat_response(
    service: ChatService,
    message: str,
) -> AsyncIterator[str]:
    """Translate chat-service chunks into the Avalo SSE protocol."""
    try:
        async for chunk in service.stream_response(message):
            yield format_sse_event("chunk", {"text": chunk})
    except RuntimeError:
        yield format_sse_event("error", {})
        return

    yield format_sse_event("done", {})


@router.post("")
async def create_chat_response(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """Stream one text-chat response as Avalo SSE events."""
    return StreamingResponse(
        stream_chat_response(service, request.message),
        media_type="text/event-stream",
    )

