import asyncio
from collections.abc import AsyncIterator

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.api.routes import chat as chat_route
from app.api.routes.chat import (
    create_chat_response,
    get_chat_service,
    stream_chat_response,
)
from app.api.schemas import ChatRequest
from app.main import create_app
from app.mcp.security import bearer_token_for_principal
from app.config import LlmConfig
from app.services.chat import (
    ChatCompressionFailedError,
    ChatNotFoundError,
    ChatTurn,
)


class FakeChatService:
    def __init__(
        self,
        chunks: list[str] | None = None,
        error: RuntimeError | None = None,
        chat_id: int = 42,
    ) -> None:
        self._chunks = chunks or []
        self._error = error
        self._chat_id = chat_id

    def start_turn(
        self,
        chat_id: int | None,
        message: str,
    ) -> ChatTurn:
        del message

        if chat_id == 999:
            raise ChatNotFoundError("Chat 999 does not exist.")
        if chat_id == 998:
            raise ChatCompressionFailedError("chat_context_compression_failed")

        return ChatTurn(
            chat_id=chat_id or self._chat_id,
            messages=[{"role": "user", "content": "Hallo"}],
        )

    async def stream_response(
        self,
        turn: ChatTurn,
    ) -> AsyncIterator[str]:
        del turn

        for chunk in self._chunks:
            yield chunk

        if self._error is not None:
            raise self._error

    async def finalize_turn(self, turn: ChatTurn) -> None:
        """Accept optional post-response finalization."""
        del turn

    def persist_stream_error(self, turn: ChatTurn, error: Exception) -> None:
        del turn, error


@pytest.mark.parametrize(
    ("tool_support", "has_tool_runner"),
    [(False, False), (True, True)],
)
def test_chat_service_creates_tool_runner_only_for_tool_capable_llm(
    monkeypatch: pytest.MonkeyPatch,
    tool_support: bool,
    has_tool_runner: bool,
) -> None:
    disposed = False

    class FakeEngine:
        def dispose(self) -> None:
            nonlocal disposed
            disposed = True

    state = type(
        "State",
        (),
        {
            "current_llm": LlmConfig(
                "test", "example:model", tool_support=tool_support
            ),
            "current_avatar": None,
            "agents": (),
        },
    )()

    monkeypatch.setattr(chat_route, "create_database_engine", lambda: FakeEngine())
    monkeypatch.setattr(chat_route, "create_session_factory", lambda engine: object())
    monkeypatch.setattr(chat_route, "ChatRepository", lambda factory: object())
    monkeypatch.setattr(chat_route, "get_avalon_state", lambda: state)
    monkeypatch.setattr(
        chat_route,
        "build_command_registry",
        lambda state, repository: object(),
    )

    service_factory = chat_route.get_chat_service()
    service = next(service_factory)

    assert (service._tool_runner is not None) is has_tool_runner

    with pytest.raises(StopIteration):
        next(service_factory)
    assert disposed is True


def post_chat(
    payload: dict,
    service: FakeChatService | None = None,
):
    async def request_chat():
        application = create_app()

        if service is not None:
            application.dependency_overrides[get_chat_service] = lambda: service

        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/api/v1/chat",
                json=payload,
                headers={"Authorization": f"Bearer {bearer_token_for_principal(1)}"},
            )

    return asyncio.run(request_chat())


def test_chat_streams_chat_id_chunks_and_done_event() -> None:
    response = post_chat(
        {"message": "Hallo"},
        FakeChatService(["Hallo ", "Flo"]),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text == (
        'event: chat\ndata: {"id": "42"}\n\n'
        'event: chunk\ndata: {"text": "Hallo "}\n\n'
        'event: chunk\ndata: {"text": "Flo"}\n\n'
        "event: done\ndata: {}\n\n"
    )


def test_chat_streams_command_response_as_regular_chunk() -> None:
    class CommandChatService(FakeChatService):
        def start_turn(
            self,
            chat_id: int | None,
            message: str,
        ) -> ChatTurn:
            del message
            return ChatTurn(
                chat_id=chat_id or 42,
                messages=[],
                command_response="ok",
            )

        async def stream_response(
            self,
            turn: ChatTurn,
        ) -> AsyncIterator[str]:
            assert turn.command_response is not None
            yield turn.command_response

    response = post_chat(
        {"message": "/test echo payload"},
        CommandChatService(),
    )

    assert response.status_code == 200
    assert response.text == (
        'event: chat\ndata: {"id": "42"}\n\n'
        'event: chunk\ndata: {"text": "ok"}\n\n'
        "event: done\ndata: {}\n\n"
    )


def test_chat_continues_existing_chat() -> None:
    response = post_chat(
        {"chat_id": 7, "message": "Weiter"},
        FakeChatService(["Antwort"]),
    )

    assert response.status_code == 200
    assert response.text.startswith(
        'event: chat\ndata: {"id": "7"}\n\n'
    )


def test_chat_streams_error_event_without_done() -> None:
    response = post_chat(
        {"message": "Hallo"},
        FakeChatService(
            ["Hallo"],
            RuntimeError("runtime failed"),
        ),
    )

    assert response.status_code == 200
    assert response.text == (
        'event: chat\ndata: {"id": "42"}\n\n'
        'event: chunk\ndata: {"text": "Hallo"}\n\n'
        "event: error\ndata: {}\n\n"
    )


def test_chat_rejects_empty_message() -> None:
    response = post_chat({"message": ""}, FakeChatService())

    assert response.status_code == 422


def test_chat_rejects_unknown_chat() -> None:
    response = post_chat(
        {"chat_id": 999, "message": "Hallo"},
        FakeChatService(),
    )

    assert response.status_code == 404


def test_chat_rejects_terminal_compression_failure() -> None:
    async def request() -> None:
        with pytest.raises(HTTPException) as error:
            await create_chat_response(
                ChatRequest(chat_id=998, message="Weiter"),
                FakeChatService(),  # type: ignore[arg-type]
            )
        assert error.value.status_code == 409
        assert error.value.detail == "chat_context_compression_failed"

    asyncio.run(request())


@pytest.mark.asyncio
async def test_chat_stream_propagates_cancellation() -> None:
    started = asyncio.Event()

    class BlockingChatService:
        async def stream_response(
            self,
            turn: ChatTurn,
        ) -> AsyncIterator[str]:
            del turn
            yield "Hallo"
            started.set()
            await asyncio.Event().wait()

    turn = ChatTurn(
        chat_id=42,
        messages=[{"role": "user", "content": "Hallo"}],
    )
    stream = stream_chat_response(BlockingChatService(), turn)

    first_event = await anext(stream)
    assert first_event == 'event: chat\ndata: {"id": "42"}\n\n'

    second_event = await anext(stream)
    assert second_event == 'event: chunk\ndata: {"text": "Hallo"}\n\n'

    task = asyncio.create_task(anext(stream))
    await started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
