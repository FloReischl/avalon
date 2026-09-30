"""Stateless local LLM inference endpoints."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.api.schemas import LlmTextRequest, LlmTextResponse
from app.runtime.ollama import OllamaRuntime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/text", response_model=LlmTextResponse)
async def generate_text(request: LlmTextRequest) -> LlmTextResponse:
    """Run non-streaming text inference without chat state or persistence."""
    messages = [
        {"role": message.role, "content": message.content}
        for message in request.messages
    ]

    try:
        content = await OllamaRuntime().generate_text_messages(messages)
    except RuntimeError as exc:
        logger.exception("[llm] text inference failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM text inference failed.",
        ) from exc

    return LlmTextResponse(content=content)
