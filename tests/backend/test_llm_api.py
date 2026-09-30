"""Tests for stateless LLM text inference."""

import pytest
from fastapi import HTTPException

from app.api.routes import llm
from app.api.schemas import LlmTextMessage, LlmTextRequest


@pytest.mark.asyncio
async def test_generate_text_passes_messages_without_chat_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_messages: list[dict[str, str]] | None = None

    async def fake_generate_text_messages(
        self,
        messages: list[dict[str, str]],
    ) -> str:
        nonlocal captured_messages
        captured_messages = messages
        return "Workflow response"

    monkeypatch.setattr(
        llm.OllamaRuntime,
        "generate_text_messages",
        fake_generate_text_messages,
    )

    request = LlmTextRequest(
        messages=[
            LlmTextMessage(role="system", content="Workflow instructions"),
            LlmTextMessage(role="user", content="Process payload"),
        ]
    )

    response = await llm.generate_text(request)

    assert response.content == "Workflow response"
    assert captured_messages == [
        {"role": "system", "content": "Workflow instructions"},
        {"role": "user", "content": "Process payload"},
    ]


@pytest.mark.asyncio
async def test_generate_text_maps_runtime_failure_to_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_generate_text_messages(
        self,
        messages: list[dict[str, str]],
    ) -> str:
        raise RuntimeError("Ollama unavailable")

    monkeypatch.setattr(
        llm.OllamaRuntime,
        "generate_text_messages",
        fake_generate_text_messages,
    )

    request = LlmTextRequest(
        messages=[LlmTextMessage(role="user", content="Hallo")]
    )

    with pytest.raises(HTTPException) as exc_info:
        await llm.generate_text(request)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "LLM text inference failed."