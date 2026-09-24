"""Text-chat streaming endpoint."""

import json
import logging
from collections.abc import AsyncIterator
import asyncio

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
from app.authorization.guard import PermissionGuard
from app.authorization.permissions import build_permission_registry
from app.authorization.runtime import get_authorization_request_manager
from app.authorization.types import AuthorizationRequest
from app.services.tool_runner import ToolRunner
from app.services.web_search import WebSearchService
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
        authorization_events: asyncio.Queue[object] = asyncio.Queue()
        guard = PermissionGuard(
            AuthorizationRepository(create_session_factory(engine)),
            build_permission_registry(),
            get_authorization_request_manager(),
            request_observer=authorization_events.put_nowait,
        )

        yield ChatService(
            OllamaRuntime(),
            repository,
            state.current_avatar,
            build_command_registry(state),
            tool_runner=ToolRunner(OllamaRuntime(), guard, WebSearchService()),
            authorization_events=authorization_events,
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

    authorization_events = getattr(service, "authorization_events", None)
    if authorization_events is None:
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
        return

    output: asyncio.Queue[tuple[str, object]] = asyncio.Queue()

    async def produce() -> None:
        try:
            async for chunk in service.stream_response(turn):
                await output.put(("chunk", chunk))
        except Exception as exc:
            await output.put(("error", exc))
        else:
            await output.put(("done", None))

    producer = asyncio.create_task(produce())
    response_text = ""
    try:
        while True:
            output_task = asyncio.create_task(output.get())
            request_task = asyncio.create_task(authorization_events.get())
            done, pending = await asyncio.wait(
                {output_task, request_task}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            task = next(iter(done))
            value = task.result()
            if task is request_task:
                request = value
                assert isinstance(request, AuthorizationRequest)
                yield format_sse_event("authorization_required", {
                    "id": request.id,
                    "context": request.context,
                    "key": request.key,
                    "items": json.dumps(request.formatted_items),
                    "validity_type": request.validity_type,
                    "default_expiry": str(request.default_expiry),
                })
                continue
            kind, payload = value
            if kind == "chunk":
                assert isinstance(payload, str)
                response_text += payload
                yield format_sse_event("chunk", {"text": payload})
                continue
            if kind == "error":
                logger.error("[chat] response stream failed: %s", payload)
                yield format_sse_event("error", {"code": type(payload).__name__})
                return
            break
    finally:
        if not producer.done():
            producer.cancel()
            await asyncio.gather(producer, return_exceptions=True)

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
