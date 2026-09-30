"""Tests for the Ollama runtime adapter."""

import asyncio

import pytest
from httpx import ConnectError
from pytest_httpx import HTTPXMock

from app.config import LlmConfig, settings
from app.runtime.ollama import OllamaRuntime, _normalize_qwen_text_tool_call


STANDARD_LLM = LlmConfig(key="standard", model="test:standard", tool_support=True)


class FakeRuntimeState:
    def __init__(self) -> None:
        self.current_llm = STANDARD_LLM
        self.begin_calls = 0
        self.end_calls = 0
        self.llm_switch_active = False

    def begin_llm_inference(self) -> None:
        self.begin_calls += 1

    def end_llm_inference(self) -> None:
        self.end_calls += 1


@pytest.fixture(autouse=True)
def runtime_state(
    monkeypatch: pytest.MonkeyPatch,
) -> FakeRuntimeState:
    state = FakeRuntimeState()
    monkeypatch.setattr(
        "app.runtime.ollama.get_avalon_state",
        lambda: state,
    )
    return state


@pytest.mark.asyncio
async def test_health_returns_true_when_model_is_available(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        match_json={"model": STANDARD_LLM.model},
        url=f"http://{settings.ollama_host}/api/show",
        json={"details": {"format": "gguf"}},
    )

    runtime = OllamaRuntime()

    assert await runtime.health() is True


@pytest.mark.asyncio
async def test_health_returns_false_when_model_is_missing(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/api/show",
        match_json={"model": STANDARD_LLM.model},
        status_code=404,
        json={"error": "model not found"},
    )

    runtime = OllamaRuntime()

    assert await runtime.health() is False


@pytest.mark.asyncio
async def test_health_returns_false_when_ollama_is_unreachable(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_exception(
        ConnectError("connection failed"),
        method="POST",
        url=f"http://{settings.ollama_host}/api/show",
    )

    runtime = OllamaRuntime()

    assert await runtime.health() is False


@pytest.mark.asyncio
async def test_model_exists_checks_explicit_model(
    httpx_mock: HTTPXMock,
) -> None:
    model = "example:model"
    httpx_mock.add_response(
        method="POST",
        match_json={"model": model},
        url=f"http://{settings.ollama_host}/api/show",
        json={"details": {"format": "gguf"}},
    )

    assert await OllamaRuntime().model_exists(model) is True


@pytest.mark.asyncio
async def test_unload_model_uses_zero_keep_alive(
    httpx_mock: HTTPXMock,
) -> None:
    model = "example:model"
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/api/generate",
        match_json={
            "model": model,
            "keep_alive": 0,
        },
        json={"done": True},
    )

    await OllamaRuntime().unload_model(model)


@pytest.mark.asyncio
async def test_warm_up_model_uses_explicit_model(
    httpx_mock: HTTPXMock,
) -> None:
    model = "example:model"
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/api/chat",
        match_json={
            "model": model,
            "messages": [{"role": "user", "content": "Hallo"}],
            "stream": False,
            "keep_alive": "1h",
        },
        json={"message": {"role": "assistant", "content": "Hallo"}},
    )

    await OllamaRuntime().warm_up_model(model)


@pytest.mark.asyncio
async def test_warm_up_uses_stateless_text_generation(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/api/chat",
        match_json={
            "model": STANDARD_LLM.model,
            "messages": [{"role": "user", "content": "Hallo"}],
            "stream": False,
            "keep_alive": "1h",
        },
        json={"message": {"role": "assistant", "content": "Hallo"}},
    )

    await OllamaRuntime().warm_up()


@pytest.mark.asyncio
async def test_generate_tool_response_normalizes_qwen_text_json_tool_call(
    httpx_mock: HTTPXMock,
    runtime_state: FakeRuntimeState,
) -> None:
    runtime_state.current_llm = LlmConfig(
        key="qwen",
        model="qwen2.5-coder:7b-instruct-ctx16k",
    )
    messages = [{"role": "user", "content": "Suche Avalon."}]
    tools = [{"type": "function", "function": {"name": "web.search"}}]
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/api/chat",
        match_json={
            "model": runtime_state.current_llm.model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "keep_alive": "1h",
        },
        json={
            "message": {
                "role": "assistant",
                "content": '{"name":"web.search","arguments":{"query":"Avalon"}}',
            }
        },
    )

    response = await OllamaRuntime().generate_tool_response(messages, tools)

    assert response == {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"function": {"name": "web.search", "arguments": {"query": "Avalon"}}}
        ],
    }


@pytest.mark.parametrize(
    ("model", "message"),
    [
        ("qwen2.5-coder:7b-instruct", {"content": "not json"}),
        (
            "qwen2.5-coder:7b-instruct",
            {"content": '{"name":"web.search","arguments":{},"extra":true}'},
        ),
        (
            "gemma4:e4b-it-q4_K_M-ctx16k",
            {"content": '{"name":"web.search","arguments":{}}'},
        ),
    ],
)
def test_qwen_text_tool_call_normalizer_preserves_non_matching_content(
    model: str,
    message: dict[str, object],
) -> None:
    assert _normalize_qwen_text_tool_call(model, message) == message


@pytest.mark.asyncio
async def test_generate_text_rejects_inference_during_llm_switch(
    runtime_state: FakeRuntimeState,
) -> None:
    runtime_state.llm_switch_active = True

    with pytest.raises(RuntimeError, match="LLM switch is in progress"):
        await OllamaRuntime().generate_text("Hallo")

    assert runtime_state.begin_calls == 0
    assert runtime_state.end_calls == 0


@pytest.mark.asyncio
async def test_generate_text_returns_response(
    httpx_mock: HTTPXMock,
    runtime_state: FakeRuntimeState,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/api/chat",
        match_json={
            "model": STANDARD_LLM.model,
            "messages": [{"role": "user", "content": "Hallo"}],
            "stream": False,
            "keep_alive": "1h",
        },
        json={"message": {"role": "assistant", "content": "Hallo Flo"}},
    )

    runtime = OllamaRuntime()

    result = await runtime.generate_text("Hallo")

    assert result == "Hallo Flo"
    assert runtime_state.begin_calls == 1
    assert runtime_state.end_calls == 1


@pytest.mark.asyncio
async def test_generate_text_messages_passes_messages_unchanged(
    httpx_mock: HTTPXMock,
) -> None:
    messages = [
        {"role": "system", "content": "Antworte knapp."},
        {"role": "user", "content": "Hallo"},
    ]
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/api/chat",
        match_json={
            "model": STANDARD_LLM.model,
            "messages": messages,
            "stream": False,
            "keep_alive": "1h",
        },
        json={"message": {"role": "assistant", "content": "Hallo Flo"}},
    )

    result = await OllamaRuntime().generate_text_messages(messages)

    assert result == "Hallo Flo"


@pytest.mark.asyncio
async def test_generate_text_raises_runtime_error_when_ollama_is_unreachable(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_exception(
        ConnectError("connection failed"),
        method="POST",
        url=f"http://{settings.ollama_host}/api/chat",
    )

    runtime = OllamaRuntime()

    with pytest.raises(RuntimeError, match="Ollama error"):
        await runtime.generate_text("Hallo")


@pytest.mark.asyncio
async def test_generate_text_raises_runtime_error_for_invalid_response(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/api/chat",
        json={"message": {"role": "assistant", "content": ""}},
    )

    runtime = OllamaRuntime()

    with pytest.raises(RuntimeError, match="Ollama error"):
        await runtime.generate_text("Hallo")


@pytest.mark.asyncio
async def test_generate_text_stream_includes_context_and_returns_chunks_in_order(
    httpx_mock: HTTPXMock,
) -> None:
    messages = [
        {"role": "user", "content": "Mein Name ist Flo."},
        {"role": "assistant", "content": "Hallo Flo."},
        {"role": "user", "content": "Wie heiße ich?"},
    ]
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/api/chat",
        match_json={
            "model": STANDARD_LLM.model,
            "messages": messages,
            "stream": True,
            "keep_alive": "1h",
        },
        content=(
            b'{"message":{"role":"assistant","content":"Du "},"done":false}\n'
            b'{"message":{"role":"assistant","content":"heisst Flo."},"done":false}\n'
            b'{"message":{"role":"assistant","content":""},"done":true}\n'
        ),
    )

    runtime = OllamaRuntime()

    chunks = [
        chunk
        async for chunk in runtime.generate_text_stream(messages)
    ]

    assert chunks == ["Du ", "heisst Flo."]


@pytest.mark.asyncio
async def test_generate_text_stream_skips_empty_chunks(
    httpx_mock: HTTPXMock,
) -> None:
    messages = [{"role": "user", "content": "Hallo"}]
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/api/chat",
        content=(
            b'{"message":{"role":"assistant","content":""},"done":false}\n'
            b'{"message":{"role":"assistant","content":"Hallo"},"done":false}\n'
            b'{"message":{"role":"assistant","content":""},"done":true}\n'
        ),
    )

    runtime = OllamaRuntime()

    chunks = [
        chunk
        async for chunk in runtime.generate_text_stream(messages)
    ]

    assert chunks == ["Hallo"]


@pytest.mark.asyncio
async def test_generate_text_stream_raises_runtime_error_for_invalid_chunk(
    httpx_mock: HTTPXMock,
) -> None:
    messages = [{"role": "user", "content": "Hallo"}]
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/api/chat",
        content=(
            b'{"message":{"role":"assistant","content":42},"done":false}\n'
        ),
    )

    runtime = OllamaRuntime()

    with pytest.raises(RuntimeError, match="Ollama error"):
        _ = [
            chunk
            async for chunk in runtime.generate_text_stream(messages)
        ]


@pytest.mark.asyncio
async def test_generate_text_stream_raises_runtime_error_when_ollama_is_unreachable(
    httpx_mock: HTTPXMock,
) -> None:
    messages = [{"role": "user", "content": "Hallo"}]
    httpx_mock.add_exception(
        ConnectError("connection failed"),
        method="POST",
        url=f"http://{settings.ollama_host}/api/chat",
    )

    runtime = OllamaRuntime()

    with pytest.raises(RuntimeError, match="Ollama error"):
        _ = [
            chunk
            async for chunk in runtime.generate_text_stream(messages)
        ]


@pytest.mark.asyncio
async def test_generate_text_stream_closes_http_stream_when_cancelled(
    monkeypatch: pytest.MonkeyPatch,
    runtime_state: FakeRuntimeState,
) -> None:
    response_exited = False
    client_exited = False
    waiting = asyncio.Event()

    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        async def aiter_lines(self):
            yield '{"message":{"role":"assistant","content":"Hallo"},"done":false}'
            waiting.set()
            await asyncio.Event().wait()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            nonlocal response_exited
            response_exited = True

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            nonlocal client_exited
            client_exited = True

        def stream(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(
        "app.runtime.ollama.httpx.AsyncClient",
        FakeClient,
    )

    runtime = OllamaRuntime()
    stream = runtime.generate_text_stream(
        [{"role": "user", "content": "Hallo"}],
    )

    assert await anext(stream) == "Hallo"

    task = asyncio.create_task(anext(stream))
    await waiting.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert response_exited is True
    assert client_exited is True
    assert runtime_state.begin_calls == 1
    assert runtime_state.end_calls == 1
