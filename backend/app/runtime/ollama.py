"""Ollama text-generation runtime adapter."""

import json
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

import httpx

from app.config import settings
from app.runtime.base import ModelRuntime
from app.state import AvalonState, get_avalon_state

OLLAMA_KEEP_ALIVE = "1h"


def _normalize_qwen_text_tool_call(
    model: str, message: dict[str, object]
) -> dict[str, object]:
    """Map Qwen2.5-Coder's text-JSON tool call to Ollama's native shape.

    Some Qwen2.5-Coder variants return the JSON object requested by their
    Modelfile as assistant content, without the ``<tool_call>`` delimiters
    Ollama needs to populate ``tool_calls``. Only accept one complete and
    unambiguous call object; all other assistant content remains text.
    """
    is_qwen_coder = model == "qwen2.5-coder" or model.startswith(
        "qwen2.5-coder:"
    )
    if not is_qwen_coder or message.get("tool_calls"):
        return message

    content = message.get("content")
    if not isinstance(content, str):
        return message
    try:
        call = json.loads(content)
    except json.JSONDecodeError:
        return message

    if (
        not isinstance(call, dict)
        or set(call) != {"name", "arguments"}
        or not isinstance(call["name"], str)
        or not isinstance(call["arguments"], dict)
    ):
        return message

    return {
        **message,
        "content": "",
        "tool_calls": [{"function": call}],
    }


class OllamaRuntime(ModelRuntime):
    """Ollama adapter for text-only local language models."""

    def __init__(
        self,
        state_provider: Callable[[], AvalonState] | None = None,
    ) -> None:
        self._state_provider = state_provider

    def _state(self) -> AvalonState:
        return (
            self._state_provider()
            if self._state_provider is not None
            else get_avalon_state()
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
                    f"http://{settings.ollama_host}/api/chat",
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": "Hallo"}],
                        "stream": False,
                        "keep_alive": OLLAMA_KEEP_ALIVE,
                    },
                )
                response.raise_for_status()
                message = response.json().get("message")
                if not isinstance(message, dict) or not isinstance(
                    message.get("content"), str
                ):
                    raise ValueError("Invalid Ollama response")
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
            raise RuntimeError(f"Ollama error: {exc}") from exc

    async def warm_up(self) -> None:
        await self.generate_text("Hallo")

    async def generate_text(self, message: str) -> str:
        return await self.generate_text_messages(
            [{"role": "user", "content": message}]
        )

    async def generate_text_messages(
        self,
        messages: list[dict[str, str]],
    ) -> str:
        async with self._inference_model() as model:
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        f"http://{settings.ollama_host}/api/chat",
                        json={
                            "model": model,
                            "messages": messages,
                            "stream": False,
                            "keep_alive": OLLAMA_KEEP_ALIVE,
                        },
                    )
                    response.raise_for_status()
                    response_message = response.json().get("message")
                    if not isinstance(response_message, dict):
                        raise ValueError("Invalid Ollama response")
                    text = response_message.get("content")
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
                        f"http://{settings.ollama_host}/api/chat",
                        json={
                            "model": model,
                            "messages": messages,
                            "stream": True,
                            "keep_alive": OLLAMA_KEEP_ALIVE,
                        },
                    ) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            message = json.loads(line).get("message")
                            if not isinstance(message, dict):
                                raise ValueError("Invalid Ollama stream response")
                            text = message.get("content")
                            if text is None:
                                continue
                            if not isinstance(text, str):
                                raise ValueError("Invalid Ollama stream response")
                            if text:
                                yield text
            except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
                raise RuntimeError(f"Ollama error: {exc}") from exc

    async def generate_tool_response_stream(
        self,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
    ) -> AsyncIterator[dict[str, object]]:
        """Stream one native Ollama tool-capable turn.

        Qwen2.5-Coder text-JSON tool calls must be buffered until the complete
        assistant message is available so they can be normalized without
        leaking the tool-call JSON as visible assistant text.
        """
        async with self._inference_model() as model:
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    async with client.stream(
                        "POST",
                        f"http://{settings.ollama_host}/api/chat",
                        json={
                            "model": model,
                            "messages": messages,
                            "tools": tools,
                            "stream": True,
                            "keep_alive": OLLAMA_KEEP_ALIVE,
                        },
                    ) as response:
                        response.raise_for_status()

                        is_qwen_coder = model == "qwen2.5-coder" or model.startswith(
                            "qwen2.5-coder:"
                        )
                        qwen_content: list[str] = []
                        qwen_tool_calls: list[object] = []

                        async for line in response.aiter_lines():
                            if not line:
                                continue

                            message = json.loads(line).get("message")
                            if not isinstance(message, dict):
                                raise ValueError("Invalid Ollama tool stream response")

                            content = message.get("content")
                            if content is not None and not isinstance(content, str):
                                raise ValueError("Invalid Ollama tool stream response")

                            tool_calls = message.get("tool_calls")
                            if tool_calls is not None and not isinstance(tool_calls, list):
                                raise ValueError("Invalid Ollama tool stream response")

                            if is_qwen_coder:
                                if content:
                                    qwen_content.append(content)
                                if tool_calls:
                                    qwen_tool_calls.extend(tool_calls)
                                continue

                            if content or tool_calls:
                                yield message

                        if is_qwen_coder:
                            complete_message: dict[str, object] = {
                                "content": "".join(qwen_content),
                            }
                            if qwen_tool_calls:
                                complete_message["tool_calls"] = qwen_tool_calls

                            normalized = _normalize_qwen_text_tool_call(
                                model, complete_message
                            )
                            if normalized.get("content") or normalized.get("tool_calls"):
                                yield normalized
            except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
                raise RuntimeError(f"Ollama error: {exc}") from exc

    async def generate_tool_response(
        self,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
    ) -> dict[str, object]:
        """Run one non-streaming native Ollama tool-calling turn."""
        async with self._inference_model() as model:
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        f"http://{settings.ollama_host}/api/chat",
                        json={
                            "model": model,
                            "messages": messages,
                            "tools": tools,
                            "stream": False,
                            "keep_alive": OLLAMA_KEEP_ALIVE,
                        },
                    )
                    response.raise_for_status()
                    message = response.json().get("message")
                    if not isinstance(message, dict):
                        raise ValueError("Invalid Ollama tool response")
                    return _normalize_qwen_text_tool_call(model, message)
            except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
                raise RuntimeError(f"Ollama error: {exc}") from exc
