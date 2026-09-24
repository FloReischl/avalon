"""Public request and response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Backend readiness information."""

    status: Literal["ok"] = "ok"
    service: str


class UiSpriteRegionResponse(BaseModel):
    """One rectangular sprite region exposed to the frontend."""

    x: int
    y: int
    width: int
    height: int


class UiStandardImageResponse(BaseModel):
    """Static base image of the effective avatar."""

    key: Literal["standard"] = "standard"
    url: str


class UiAnimationResponse(BaseModel):
    """One configured animation of the effective avatar."""

    key: str
    category: str
    spriteSetUrl: str
    sprites: list[UiSpriteRegionResponse]


class UiAvatarResponse(BaseModel):
    """Frontend rendering configuration for the effective avatar."""

    greetingAudioUrl: str
    standard: UiStandardImageResponse
    animations: list[UiAnimationResponse]


class UiConfigResponse(BaseModel):
    """Configuration intentionally exposed to the frontend."""

    name: str
    avatar: UiAvatarResponse


class ChatRequest(BaseModel):

    """One new text-chat turn."""

    chat_id: int | None = Field(default=None, gt=0)
    message: str = Field(min_length=1)


class ConversationMessage(BaseModel):
    """One previous plain-text conversation message."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class PersistentMessageResponse(BaseModel):
    """One persistent message returned by the chat-management API."""

    id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class ChatSummaryResponse(BaseModel):
    """One persistent chat for sidebar-style listings."""

    id: int
    title: str
    pinned: bool
    created_at: datetime



class ChatDetailResponse(ChatSummaryResponse):
    """One persistent chat including its complete message history."""

    messages: list[PersistentMessageResponse]
    compression_error_code: str | None = None


class RenameChatRequest(BaseModel):
    """Requested manual title for one persistent chat."""

    title: str = Field(min_length=1, max_length=200)


class SetChatPinnedRequest(BaseModel):
    """Requested pinned state for one persistent chat."""

    pinned: bool


class AudioResponseRequest(BaseModel):

    """Conversation context accompanying a completed audio turn."""

    chat_id: int | None = Field(default=None, gt=0)
    messages: list[ConversationMessage] = Field(default_factory=list)


class AudioCallStartRequest(BaseModel):
    """Start Avalon's one avatar audio call, optionally bound to a chat."""

    chat_id: int | None = Field(default=None, gt=0)


class AudioCallStatusResponse(BaseModel):
    """Frontend-visible state of Avalon's one avatar audio call."""

    active: bool
    chat_id: int | None
    turn_active: bool
    pending_speech: str | None = None


class TtsRequest(BaseModel):
    """Plain text to synthesize as local speech."""

    text: str = Field(min_length=1)


class TtsPlaybackEndedRequest(BaseModel):
    """Identify the playback that has stopped in the frontend."""

    playback_id: str = Field(min_length=1)
