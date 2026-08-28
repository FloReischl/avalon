"""Tests for the Ollama runtime adapter."""

import pytest
from httpx import ConnectError
from pytest_httpx import HTTPXMock
from app.config import settings
from app.runtime.ollama import OllamaRuntime
import base64
from pathlib import Path

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
        await runtime.generate_text("Hallo")


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
    with open("tests/data/german-transcription.wav", "rb") as f:
        audio_data = f.read()
    audio_base64 = base64.b64encode(audio_data).decode("utf-8")

    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/v1/chat/completions",
        json={"response": ""},
    )

    runtime = OllamaRuntime()

    with pytest.raises(RuntimeError, match="Ollama error"):
        await runtime.generate_from_audio(Path("tests/data/german-transcription.wav"))
