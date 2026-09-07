"""Public request and response schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Backend readiness information."""

    status: Literal["ok"] = "ok"
    service: str


class ChatRequest(BaseModel):
    """One new text-chat turn."""

    chat_id: int | None = Field(default=None, gt=0)
    message: str = Field(min_length=1)


class ConversationMessage(BaseModel):
    """One previous plain-text conversation message."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class AudioResponseRequest(BaseModel):
    """Conversation context accompanying a completed audio turn."""

    messages: list[ConversationMessage] = Field(default_factory=list)


class TtsRequest(BaseModel):
    """Plain text to synthesize as local speech."""

    text: str = Field(min_length=1)


class TtsPlaybackEndedRequest(BaseModel):
    """Identify the playback that has stopped in the frontend."""

    playback_id: str = Field(min_length=1)


