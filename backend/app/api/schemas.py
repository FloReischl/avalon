"""Public request and response schemas."""

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


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
    agentBearerToken: str
    avatarZoom: float
    avatar: UiAvatarResponse


class AgentTokenResponse(BaseModel):
    """Bearer token for one persisted agent."""

    agentBearerToken: str


class UserSettingsUpdateRequest(BaseModel):
    """Request payload for updating user settings."""

    avatar_zoom: float | None = Field(default=None, ge=0.5, le=1.5)
    avatarZoom: float | None = Field(default=None, ge=0.5, le=1.5)

    @model_validator(mode="after")
    def validate_zoom(self) -> Self:
        zoom = self.avatar_zoom if self.avatar_zoom is not None else self.avatarZoom
        if zoom is None:
            raise ValueError("avatar_zoom or avatarZoom is required.")
        return self


class ChatRequest(BaseModel):

    """One new text-chat turn."""

    chat_id: int | None = Field(default=None, gt=0)
    message: str = Field(min_length=1)


class AuthorizationDecisionRequest(BaseModel):
    """One browser decision for a pending authorization request."""

    approved_item_indexes: list[int] = Field(default_factory=list)
    duration_seconds: int | None = Field(default=None, ge=1, le=365 * 24 * 60 * 60)


class PendingAuthorizationRequestResponse(BaseModel):
    id: str
    context: str
    key: str
    items: list[str]
    validity_type: Literal["permanent", "duration", "range"]
    default_expiry: int
    source_label: str


class ProactivePermissionGrantResponse(BaseModel):
    id: int
    expires_at: datetime


class ProactivePermissionResponse(BaseModel):
    id: int
    context: str
    key: str
    validity_type: Literal["permanent", "duration", "range"]
    default_expiry: int
    grant: ProactivePermissionGrantResponse | None = None
    read_only: bool = False


class ProactivePermissionUpdateRequest(BaseModel):
    granted: bool = True
    expires_at: datetime | None = None


class ConversationMessage(BaseModel):
    """One previous plain-text conversation message."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class LlmTextMessage(BaseModel):
    """One message passed directly to the configured text model."""

    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class LlmTextRequest(BaseModel):
    """Stateless non-streaming text inference request."""

    messages: list[LlmTextMessage] = Field(min_length=1)


class LlmTextResponse(BaseModel):
    """Stateless text inference result."""

    content: str


class TextMessageResponse(BaseModel):
    id: int
    kind: Literal["text"] = "text"
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    attachments: list["AttachmentResponse"] = Field(default_factory=list)


class ProgressMessageResponse(BaseModel):
    id: int
    kind: Literal["progress"] = "progress"
    created_at: datetime
    updated_at: datetime
    messages: list[str]
    workflow_execution: "WorkflowExecutionResponse"


class WorkflowExecutionResponse(BaseModel):
    id: int
    workflow_key: str
    state: Literal["running", "pending", "completed", "failed", "aborted"]


class AttachmentResponse(BaseModel):
    """Metadata for one immutable attachment exposed to the UI."""

    id: int
    original_file_name: str
    mime_type: str
    size: int
    created_at: datetime


class ChatSummaryResponse(BaseModel):
    """One persistent chat for sidebar-style listings."""

    id: int
    title: str
    pinned: bool
    agent_id: int
    agent_name: str | None = None
    agent_icon: str | None = None
    created_at: datetime



class ChatDetailResponse(ChatSummaryResponse):
    """One persistent chat including its complete message history."""

    messages: list[TextMessageResponse | ProgressMessageResponse]
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


class WorkflowRuntimeUpdateRequest(BaseModel):
    state: Literal["running", "pending", "completed", "failed", "aborted"] | None = None
    progress_content: list[str] | None = None


class WorkflowConfirmationRequest(BaseModel):
    confirmation_schema: object = Field(alias="schema")
    rows: object


class WorkflowConfirmationSubmitRequest(BaseModel):
    rows: object


class WorkflowConfirmationResponse(BaseModel):
    id: str
    execution_id: int
    confirmation_schema: dict[str, object] = Field(alias="schema")
    rows: list[dict[str, object]]
