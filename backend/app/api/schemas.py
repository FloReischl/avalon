"""Public request and response schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Backend readiness information."""

    status: Literal["ok"] = "ok"
    service: str


class ChatRequest(BaseModel):
    """Conversation context including the current text-chat input."""

    messages: list["ConversationMessage"] = Field(min_length=1)


class ConversationMessage(BaseModel):
    """One previous plain-text conversation message."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class AudioResponseRequest(BaseModel):
    """Conversation context accompanying a completed audio turn."""

    messages: list[ConversationMessage] = Field(default_factory=list)

