import asyncio
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.routes.chat import get_chat_service, stream_chat_response
from app.main import create_app


class FakeChatService:
    def __init__(
        self,
        chunks: list[str] | None = None,
        error: RuntimeError | None = None,
    ) -> None:
        self._chunks = chunks or []
        self._error = error

    async def stream_response(
        self,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        del messages

        for chunk in self._chunks:
            yield chunk

        if self._error is not None:
            raise self._error


def post_chat(
    messages: list[dict[str, str]],
    service: FakeChatService | None = None,
):
    async def request_chat():
        application = create_app()

        if service is not None:
            application.dependency_overrides[get_chat_service] = lambda: service

        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/api/v1/chat", json={"messages": messages})

    return asyncio.run(request_chat())


def test_chat_streams_chunks_and_done_event() -> None:
    response = post_chat(
        [{"role": "user", "content": "Hallo"}],
        FakeChatService(["Hallo ", "Flo"]),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text == (
        'event: chunk\ndata: {"text": "Hallo "}\n\n'
        'event: chunk\ndata: {"text": "Flo"}\n\n'
        "event: done\ndata: {}\n\n"
    )


def test_chat_streams_error_event_without_done() -> None:
    response = post_chat(
        [{"role": "user", "content": "Hallo"}],
        FakeChatService(
            ["Hallo"],
            RuntimeError("runtime failed"),
        ),
    )

    assert response.status_code == 200
    assert response.text == (
        'event: chunk\ndata: {"text": "Hallo"}\n\n'
        "event: error\ndata: {}\n\n"
    )


def test_chat_rejects_empty_messages() -> None:
    response = post_chat([])

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_stream_propagates_cancellation() -> None:
    started = asyncio.Event()

    class BlockingChatService:
        async def stream_response(
            self,
            messages: list[dict[str, str]],
        ) -> AsyncIterator[str]:
            del messages
            yield "Hallo"
            started.set()
            await asyncio.Event().wait()

    stream = stream_chat_response(
        BlockingChatService(),
        [{"role": "user", "content": "Hallo"}],
    )

    first_event = await anext(stream)
    assert first_event == 'event: chunk\ndata: {"text": "Hallo"}\n\n'

    task = asyncio.create_task(anext(stream))
    await started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
