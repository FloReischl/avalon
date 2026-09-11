"""Tests for the Ollama runtime adapter."""

import asyncio
import base64
from pathlib import Path

import pytest
from httpx import ConnectError
from pytest_httpx import HTTPXMock

from app.config import settings
from app.runtime.ollama import OllamaRuntime


class FakeRuntimeState:
    def __init__(self) -> None:
        self.current_llm = next(
            llm for llm in settings.llm_models if llm.key == "standard"
        )
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
        "app.runtime.ollama.get_avalo_state",
        lambda: state,
    )
    return state


@pytest.mark.asyncio
async def test_health_returns_true_when_model_is_available(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        match_json={"model": settings.ollama_model},
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
        match_json={"model": settings.ollama_model},
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
        url=f"http://{settings.ollama_host}/api/generate",
        match_json={
            "model": model,
            "prompt": "Hallo",
            "stream": False,
        },
        json={"response": "Hallo"},
    )

    await OllamaRuntime().warm_up_model(model)


@pytest.mark.asyncio
async def test_warm_up_uses_stateless_text_generation(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/api/generate",
        match_json={
            "model": settings.ollama_model,
            "prompt": "Hallo",
            "stream": False,
        },
        json={"response": "Hallo"},
    )

    await OllamaRuntime().warm_up()


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
        url=f"http://{settings.ollama_host}/api/generate",
        match_json={
            "model": settings.ollama_model,
            "prompt": "Hallo",
            "stream": False,
        },
        json={"response": "Hallo Flo"},
    )

    runtime = OllamaRuntime()

    result = await runtime.generate_text("Hallo")

    assert result == "Hallo Flo"
    assert runtime_state.begin_calls == 1
    assert runtime_state.end_calls == 1


@pytest.mark.asyncio
async def test_generate_text_raises_runtime_error_when_ollama_is_unreachable(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_exception(
        ConnectError("connection failed"),
        method="POST",
        url=f"http://{settings.ollama_host}/api/generate",
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
        url=f"http://{settings.ollama_host}/api/generate",
        json={"response": ""},
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
        url=f"http://{settings.ollama_host}/v1/chat/completions",
        match_json={
            "model": settings.ollama_model,
            "messages": messages,
            "stream": True,
        },
        content=(
            b'data: {"choices":[{"delta":{"content":"Du "}}]}\n\n'
            b'data: {"choices":[{"delta":{"content":"heisst Flo."}}]}\n\n'
            b"data: [DONE]\n\n"
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
        url=f"http://{settings.ollama_host}/v1/chat/completions",
        content=(
            b'data: {"choices":[{"delta":{"content":""}}]}\n\n'
            b'data: {"choices":[{"delta":{"content":"Hallo"}}]}\n\n'
            b'data: {"choices":[{"delta":{"content":""}}]}\n\n'
            b"data: [DONE]\n\n"
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
        url=f"http://{settings.ollama_host}/v1/chat/completions",
        content=(
            b'data: {"choices":[{"delta":{"content":42}}]}\n\n'
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
        url=f"http://{settings.ollama_host}/v1/chat/completions",
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
            yield 'data: {"choices":[{"delta":{"content":"Hallo"}}]}'
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


@pytest.mark.asyncio
async def test_generate_from_audio_returns_response(
    httpx_mock: HTTPXMock,
) -> None:
    with open("tests/data/german-transcription.wav", "rb") as f:
        audio_data = f.read()
    audio_base64 = base64.b64encode(audio_data).decode("utf-8")

    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/v1/chat/completions",
        match_json={
            "model": settings.ollama_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Transcribe and respond in German:",
                        },
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_base64,
                                "format": "wav",
                            },
                        },
                    ],
                },
            ],
        },
        json={
            "choices": [
                {
                    "message": {
                        "content": "Die Hauptstadt von Deutschland ist Berlin.",
                    },
                },
            ],
        },
    )

    runtime = OllamaRuntime()

    result = await runtime.generate_from_audio(Path("tests/data/german-transcription.wav"))

    assert result == "Die Hauptstadt von Deutschland ist Berlin."


@pytest.mark.asyncio
async def test_generate_from_audio_stream_includes_context_and_yields_content(
    httpx_mock: HTTPXMock,
) -> None:
    audio_data = Path("tests/data/german-transcription.wav").read_bytes()
    audio_base64 = base64.b64encode(audio_data).decode("utf-8")
    context = [{"role": "user", "content": "Mein Name ist Flo."}]
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/v1/chat/completions",
        match_json={
            "model": settings.ollama_model,
            "messages": [
                *context,
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Listen to the audio and respond in German.",
                        },
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_base64,
                                "format": "wav",
                            },
                        },
                    ],
                },
            ],
            "stream": True,
        },
        content=(
            b'data: {"choices":[{"delta":{"content":"Hallo "}}]}\n\n'
            b'data: {"choices":[{"delta":{"content":"Flo"}}]}\n\n'
            b"data: [DONE]\n\n"
        ),
    )

    chunks = [
        chunk
        async for chunk in OllamaRuntime().generate_from_audio_stream(
            Path("tests/data/german-transcription.wav"),
            context,
        )
    ]

    assert chunks == ["Hallo ", "Flo"]


@pytest.mark.asyncio
async def test_generate_from_audio_raises_runtime_error_when_ollama_is_unreachable(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_exception(
        ConnectError("connection failed"),
        method="POST",
        url=f"http://{settings.ollama_host}/v1/chat/completions",
    )

    runtime = OllamaRuntime()

    with pytest.raises(RuntimeError, match="Ollama error"):
        await runtime.generate_from_audio(Path("tests/data/german-transcription.wav"))


@pytest.mark.asyncio
async def test_generate_from_audio_raises_runtime_error_for_invalid_response(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/v1/chat/completions",
        json={
            "choices": [
                {
                    "message": {
                        "content": "",
                    },
                },
            ],
        },
    )

    runtime = OllamaRuntime()

    with pytest.raises(RuntimeError, match="Ollama error"):
        await runtime.generate_from_audio(Path("tests/data/german-transcription.wav"))
