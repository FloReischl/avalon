"""Editable per-user Avalon configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator



PROJECT_ROOT = Path(__file__).resolve().parents[2]
USER_CONFIG_PATH = Path("~/.avalon/config.yaml").expanduser()

NonEmptyStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


def _resolve_runtime_path(path: Path) -> Path:
    expanded = path.expanduser()
    if not expanded.is_absolute():
        expanded = PROJECT_ROOT / expanded
    return expanded.resolve()


class StrictConfigModel(BaseModel):
    """Reject unknown configuration fields instead of silently ignoring them."""

    model_config = ConfigDict(extra="forbid")


class ChatterboxUserConfig(StrictConfigModel):
    """Reserved user-specific Chatterbox settings."""

    reference_audio: Path


class KokoroUserConfig(StrictConfigModel):
    """User-specific Kokoro artifact locations."""

    model: Path
    voice: Path
    config: Path

    @field_validator("model", "voice", "config", mode="after")
    @classmethod
    def normalize_artifact_path(cls, value: Path) -> Path:
        return _resolve_runtime_path(value)

    @model_validator(mode="after")
    def validate_artifacts(self) -> Self:
        for description, path in (
            ("model", self.model),
            ("voice", self.voice),
            ("config", self.config),
        ):
            if not path.is_file():
                raise ValueError(
                    f"Kokoro {description} artifact is missing: {path}"
                )
        return self


class TtsUserConfig(StrictConfigModel):
    """Editable TTS configuration."""

    chatterbox: ChatterboxUserConfig | None = None
    kokoro: KokoroUserConfig


class ChatUserConfig(StrictConfigModel):
    """Default chat agent."""

    agent_key: NonEmptyStr


class UserConfig(StrictConfigModel):
    """Validated editable Avalon configuration."""

    name: NonEmptyStr
    chat: ChatUserConfig
    tts: TtsUserConfig
    @property
    def chat_default_agent_key(self) -> str:
        """Return the configured default chat agent key."""
        return self.chat.agent_key


_user_config: UserConfig | None = None


def load_user_config(path: Path = USER_CONFIG_PATH) -> UserConfig:
    """Load and fully validate one user configuration file."""
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    return UserConfig.model_validate(data)


def initialize_user_config(path: Path = USER_CONFIG_PATH) -> UserConfig:
    """Load the process-local user configuration exactly once."""
    global _user_config

    if _user_config is None:
        _user_config = load_user_config(path)
    return _user_config


def get_user_config() -> UserConfig:
    """Return the initialized process-local user configuration."""
    if _user_config is None:
        raise RuntimeError("User configuration has not been initialized.")
    return _user_config
