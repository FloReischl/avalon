from collections.abc import AsyncIterator

import pytest

from app.services.tool_runner import ToolRunner


TOOL_CALL = {
    "function": {
        "name": "web.search",
        "arguments": {"query": "Avalon"},
    }
}


class FakeRuntime:
    def __init__(self, responses: list[list[dict[str, object]]]) -> None:
        self.responses = responses
        self.requests: list[list[dict[str, object]]] = []

    async def generate_tool_response_stream(
        self,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
    ) -> AsyncIterator[dict[str, object]]:
        del tools
        self.requests.append([dict(message) for message in messages])
        response = self.responses[len(self.requests) - 1]
        for chunk in response:
            yield chunk


class FakeMcpClient:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def list_tools(self) -> list[dict[str, object]]:
        return [{"type": "function", "function": {"name": "web.search"}}]

    async def call_tool(
        self, name: str, arguments: dict[str, object]
    ) -> object:
        self.calls.append((name, arguments))
        if self.error is not None:
            raise self.error
        return {"result": "found"}


@pytest.fixture(autouse=True)
def clear_tool_definition_cache() -> None:
    ToolRunner._tool_definition_cache.clear()


@pytest.mark.asyncio
async def test_stream_response_yields_text_chunks_immediately() -> None:
    runtime = FakeRuntime(
        [[{"content": "Hallo "}, {"content": "Flo"}]]
    )
    client = FakeMcpClient()
    runner = ToolRunner(runtime, lambda principal_id: client)

    stream = runner.stream_response(
        1,
        [{"role": "user", "content": "Hallo"}],
        "Chat: Test",
    )

    assert await anext(stream) == "Hallo "
    assert await anext(stream) == "Flo"

    with pytest.raises(StopAsyncIteration):
        await anext(stream)


@pytest.mark.asyncio
async def test_stream_response_continues_after_tool_call() -> None:
    runtime = FakeRuntime(
        [
            [
                {"content": "Ich schaue nach. "},
                {"content": "", "tool_calls": [TOOL_CALL]},
            ],
            [
                {"content": "Gefunden: "},
                {"content": "Avalon."},
            ],
        ]
    )
    client = FakeMcpClient()
    runner = ToolRunner(runtime, lambda principal_id: client)

    chunks = [
        chunk
        async for chunk in runner.stream_response(
            1,
            [{"role": "user", "content": "Suche Avalon"}],
            "Chat: Test",
        )
    ]

    assert chunks == [
        "Ich schaue nach. ",
        "Gefunden: ",
        "Avalon.",
    ]
    assert client.calls == [("web.search", {"query": "Avalon"})]

    second_request = runtime.requests[1]
    assert second_request[-2] == {
        "role": "assistant",
        "content": "Ich schaue nach. ",
        "tool_calls": [TOOL_CALL],
    }
    assert second_request[-1] == {
        "role": "tool",
        "content": '{"result": "found"}',
    }


@pytest.mark.asyncio
async def test_stream_response_keeps_prior_text_visible_when_tool_fails() -> None:
    runtime = FakeRuntime(
        [
            [
                {"content": "Ich versuche es. "},
                {"content": "", "tool_calls": [TOOL_CALL]},
            ]
        ]
    )
    client = FakeMcpClient(RuntimeError("tool failed"))
    runner = ToolRunner(runtime, lambda principal_id: client)

    stream = runner.stream_response(
        1,
        [{"role": "user", "content": "Suche Avalon"}],
        "Chat: Test",
    )

    assert await anext(stream) == "Ich versuche es. "

    with pytest.raises(RuntimeError, match="MCP tools/call failed"):
        await anext(stream)