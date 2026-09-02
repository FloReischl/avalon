"""Tests for the Ollama runtime adapter."""

import asyncio
import base64
from pathlib import Path

import pytest
from httpx import ConnectError
from pytest_httpx import HTTPXMock

from app.config import settings
from app.runtime.ollama import OllamaRuntime

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
async def test_generate_text_returns_response(
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
        json={"response": "Hallo Flo"},
    )

    runtime = OllamaRuntime()

    result = await runtime.generate_text("Hallo")

    assert result == "Hallo Flo"


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
async def test_generate_text_stream_returns_chunks_in_order(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/api/generate",
        match_json={
            "model": settings.ollama_model,
            "prompt": "Hallo",
            "stream": True,
        },
        content=(
            b'{"response":"Hallo "}\n'
            b'{"response":"Flo"}\n'
            b'{"response":"","done":true}\n'
        ),
    )

    runtime = OllamaRuntime()

    chunks = [
        chunk
        async for chunk in runtime.generate_text_stream("Hallo")
    ]

    assert chunks == ["Hallo ", "Flo"]


@pytest.mark.asyncio
async def test_generate_text_stream_skips_empty_chunks(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/api/generate",
        content=(
            b'{"response":""}\n'
            b'{"response":"Hallo"}\n'
            b'{"response":""}\n'
        ),
    )

    runtime = OllamaRuntime()

    chunks = [
        chunk
        async for chunk in runtime.generate_text_stream("Hallo")
    ]

    assert chunks == ["Hallo"]


@pytest.mark.asyncio
async def test_generate_text_stream_raises_runtime_error_for_invalid_chunk(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/api/generate",
        content=b'{"response":42}\n',
    )

    runtime = OllamaRuntime()

    with pytest.raises(RuntimeError, match="Ollama error"):
        _ = [
            chunk
            async for chunk in runtime.generate_text_stream("Hallo")
        ]


@pytest.mark.asyncio
async def test_generate_text_stream_raises_runtime_error_when_ollama_is_unreachable(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_exception(
        ConnectError("connection failed"),
        method="POST",
        url=f"http://{settings.ollama_host}/api/generate",
    )

    runtime = OllamaRuntime()

    with pytest.raises(RuntimeError, match="Ollama error"):
        _ = [
            chunk
            async for chunk in runtime.generate_text_stream("Hallo")
        ]


@pytest.mark.asyncio
async def test_generate_text_stream_closes_http_stream_when_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response_exited = False
    client_exited = False
    waiting = asyncio.Event()

    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        async def aiter_lines(self):
            yield '{"response":"Hallo"}'
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
    stream = runtime.generate_text_stream("Hallo")

    assert await anext(stream) == "Hallo"

    task = asyncio.create_task(anext(stream))
    await waiting.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert response_exited is True
    assert client_exited is True


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
