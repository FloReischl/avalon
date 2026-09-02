"""Public request and response schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Backend readiness information."""

    status: Literal["ok"] = "ok"
    service: str


class ChatRequest(BaseModel):
    """A single text-chat input."""

    message: str = Field(min_length=1)


