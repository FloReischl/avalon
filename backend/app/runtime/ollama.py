"""Ollama runtime adapter."""

import base64
import json
from collections.abc import AsyncIterator
from pathlib import Path

import httpx

from app.config import settings
from app.runtime.base import ModelRuntime


class OllamaRuntime(ModelRuntime):
    """Ollama runtime adapter."""

    async def health(self) -> bool:
        """Return whether the configured model is available in Ollama."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://{settings.ollama_host}/api/show",
                    json={"model": settings.ollama_model},
                )
                response.raise_for_status()
                return True
        except (httpx.RequestError, httpx.HTTPStatusError):
            return False

    async def warm_up(self) -> None:
        """Make the configured model resident without chat context."""
        await self.generate_text("Hallo")

    async def generate_text(self, message: str) -> str:
        """Generate a complete response from text input."""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"http://{settings.ollama_host}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": message,
                        "stream": False,
                    },
                )
                response.raise_for_status()

                data = response.json()
                text = data.get("response")

                if not isinstance(text, str) or not text.strip():
                    raise ValueError("Invalid Ollama response")

                return text
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
            raise RuntimeError(f"Ollama error: {exc}") from exc

    async def generate_text_stream(
        self,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        """Generate response text incrementally from chat context."""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"http://{settings.ollama_host}/v1/chat/completions",
                    json={
                        "model": settings.ollama_model,
                        "messages": messages,
                        "stream": True,
                    },
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue

                        payload = line.removeprefix("data: ")
                        if payload == "[DONE]":
                            continue

                        data = json.loads(payload)
                        choices = data.get("choices")
                        if not isinstance(choices, list) or not choices:
                            continue

                        delta = choices[0].get("delta")
                        if not isinstance(delta, dict):
                            raise ValueError("Invalid Ollama stream response")

                        text = delta.get("content")
                        if text is None:
                            continue
                        if not isinstance(text, str):
                            raise ValueError("Invalid Ollama stream response")
                        if text:
                            yield text
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
            raise RuntimeError(f"Ollama error: {exc}") from exc

    async def generate_from_audio(self, audio_file: Path) -> str:
        """Generate a complete response from native audio input."""
        try:
            with open(audio_file, "rb") as f:
                audio_data = f.read()
            audio_base64 = base64.b64encode(audio_data).decode("utf-8")

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"http://{settings.ollama_host}/v1/chat/completions",
                    json={
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
                )
                response.raise_for_status()

                data = response.json()
                choices = data.get("choices")

                if not isinstance(choices, list) or not choices:
                    raise ValueError("Invalid Ollama response")

                message = choices[0].get("message")
                if not isinstance(message, dict):
                    raise ValueError("Invalid Ollama response")

                text = message.get("content")
                if not isinstance(text, str) or not text.strip():
                    raise ValueError("Invalid Ollama response")

                return text
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
            raise RuntimeError(f"Ollama error: {exc}") from exc

    async def transcribe_audio_stream(
        self,
        audio_file: Path,
    ) -> AsyncIterator[str]:
        """Stream a plain transcription of native audio without chat context."""
        try:
            audio_base64 = base64.b64encode(audio_file.read_bytes()).decode("utf-8")

            messages: list[dict[str, object]] = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Transcribe the spoken audio. "
                                "Return only the transcription text."
                            ),
                        },
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_base64,
                                "format": "wav",
                            },
                        },
                    ],
                }
            ]

            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"http://{settings.ollama_host}/v1/chat/completions",
                    json={
                        "model": settings.ollama_model,
                        "messages": messages,
                        "stream": True,
                    },
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue

                        payload = line.removeprefix("data: ")
                        if payload == "[DONE]":
                            continue

                        data = json.loads(payload)
                        choices = data.get("choices")
                        if not isinstance(choices, list) or not choices:
                            continue

                        delta = choices[0].get("delta")
                        if not isinstance(delta, dict):
                            raise ValueError("Invalid Ollama stream response")

                        text = delta.get("content")
                        if text is None:
                            continue
                        if not isinstance(text, str):
                            raise ValueError("Invalid Ollama stream response")
                        if text:
                            yield text
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
            raise RuntimeError(f"Ollama error: {exc}") from exc

    async def generate_from_audio_stream(
        self,
        audio_file: Path,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        """Stream a response to native audio with prior chat context."""
        try:
            audio_base64 = base64.b64encode(audio_file.read_bytes()).decode("utf-8")
            ollama_messages: list[dict[str, object]] = [*messages]
            ollama_messages.append(
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
                }
            )

            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"http://{settings.ollama_host}/v1/chat/completions",
                    json={
                        "model": settings.ollama_model,
                        "messages": ollama_messages,
                        "stream": True,
                    },
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue

                        payload = line.removeprefix("data: ")
                        if payload == "[DONE]":
                            continue

                        data = json.loads(payload)
                        choices = data.get("choices")
                        if not isinstance(choices, list) or not choices:
                            continue

                        delta = choices[0].get("delta")
                        if not isinstance(delta, dict):
                            raise ValueError("Invalid Ollama stream response")

                        text = delta.get("content")
                        if text is None:
                            continue
                        if not isinstance(text, str):
                            raise ValueError("Invalid Ollama stream response")
                        if text:
                            yield text
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
            raise RuntimeError(f"Ollama error: {exc}") from exc
