"""Ollama text-generation runtime adapter."""

import json
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

import httpx

from app.config import settings
from app.runtime.base import ModelRuntime
from app.state import AvaloState, get_avalo_state


class OllamaRuntime(ModelRuntime):
    """Ollama adapter for text-only local language models."""

    def __init__(
        self,
        state_provider: Callable[[], AvaloState] | None = None,
    ) -> None:
        self._state_provider = state_provider

    def _state(self) -> AvaloState:
        return (
            self._state_provider()
            if self._state_provider is not None
            else get_avalo_state()
        )

    @asynccontextmanager
    async def _inference_model(self) -> AsyncIterator[str]:
        state = self._state()
        if state.llm_switch_active:
            raise RuntimeError("LLM switch is in progress.")
        state.begin_llm_inference()
        try:
            yield state.current_llm.model
        finally:
            state.end_llm_inference()

    async def model_exists(self, model: str) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://{settings.ollama_host}/api/show",
                    json={"model": model},
                )
                response.raise_for_status()
                return True
        except (httpx.RequestError, httpx.HTTPStatusError):
            return False

    async def health(self) -> bool:
        return await self.model_exists(self._state().current_llm.model)

    async def unload_model(self, model: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"http://{settings.ollama_host}/api/generate",
                    json={"model": model, "keep_alive": 0},
                )
                response.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            raise RuntimeError(f"Ollama error: {exc}") from exc

    async def warm_up_model(self, model: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"http://{settings.ollama_host}/api/generate",
                    json={"model": model, "prompt": "Hallo", "stream": False},
                )
                response.raise_for_status()
                if not isinstance(response.json().get("response"), str):
                    raise ValueError("Invalid Ollama response")
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
            raise RuntimeError(f"Ollama error: {exc}") from exc

    async def warm_up(self) -> None:
        await self.generate_text("Hallo")

    async def generate_text(self, message: str) -> str:
        async with self._inference_model() as model:
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        f"http://{settings.ollama_host}/api/generate",
                        json={"model": model, "prompt": message, "stream": False},
                    )
                    response.raise_for_status()
                    text = response.json().get("response")
                    if not isinstance(text, str) or not text.strip():
                        raise ValueError("Invalid Ollama response")
                    return text
            except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
                raise RuntimeError(f"Ollama error: {exc}") from exc

    async def generate_text_stream(
        self,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        async with self._inference_model() as model:
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    async with client.stream(
                        "POST",
                        f"http://{settings.ollama_host}/v1/chat/completions",
                        json={"model": model, "messages": messages, "stream": True},
                    ) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            payload = line.removeprefix("data: ")
                            if payload == "[DONE]":
                                continue
                            choices = json.loads(payload).get("choices")
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