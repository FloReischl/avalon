"""Tests for the text-chat application service."""

from collections.abc import AsyncIterator

import pytest

from app.services.chat import ChatService


class FakeRuntime:
    async def health(self) -> bool:
        return True

    async def generate_text(self, message: str) -> str:
        return message

    async def generate_text_stream(self, message: str) -> AsyncIterator[str]:
        yield f"{message} "
        yield "Flo"

    async def generate_from_audio(self, audio_file) -> str:
        raise NotImplementedError


@pytest.mark.asyncio
async def test_stream_response_forwards_runtime_chunks_in_order() -> None:
    service = ChatService(FakeRuntime())

    chunks = [
        chunk
        async for chunk in service.stream_response("Hallo")
    ]

    assert chunks == ["Hallo ", "Flo"]
