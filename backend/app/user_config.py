"""Editable per-user Avalo configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
USER_CONFIG_PATH = Path("~/.avalo/config.yaml").expanduser()

NonEmptyStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


def _resolve_runtime_path(path: Path) -> Path:
    expanded = path.expanduser()
    if not expanded.is_absolute():
        expanded = PROJECT_ROOT / expanded
    return expanded.resolve()


def resolve_avatar_asset_path(base_path: Path, asset: str) -> Path:
    """Resolve one configured avatar asset and enforce its storage boundary."""
    candidate = Path(asset).expanduser()
    if not candidate.is_absolute():
        candidate = base_path / candidate

    resolved = candidate.resolve()
    if not resolved.is_relative_to(base_path):
        raise ValueError(
            f"Avatar asset resolves outside base_path {base_path}: {asset}"
        )
    if not resolved.is_file():
        raise ValueError(f"Avatar asset is missing: {resolved}")

    return resolved


class StrictConfigModel(BaseModel):
    """Reject unknown configuration fields instead of silently ignoring them."""

    model_config = ConfigDict(extra="forbid")


class SpriteRegion(StrictConfigModel):
    """One rectangular region inside an animation sprite set."""

    x: int = Field(ge=0, strict=True)
    y: int = Field(ge=0, strict=True)
    width: int = Field(gt=0, strict=True)
    height: int = Field(gt=0, strict=True)

    @model_validator(mode="before")
    @classmethod
    def parse_compact_region(cls, value: object) -> object:
        if isinstance(value, (list, tuple)):
            if len(value) != 4:
                raise ValueError(
                    "Sprite region must contain exactly x, y, width, height."
                )
            return {
                "x": value[0],
                "y": value[1],
                "width": value[2],
                "height": value[3],
            }
        return value


class AvatarAnimationConfig(StrictConfigModel):
    """One configured avatar animation."""

    key: NonEmptyStr
    category: NonEmptyStr
    sprite_set: NonEmptyStr = Field(alias="sprite-set")
    sprites: list[SpriteRegion] = Field(min_length=1)


class AvatarImagesConfig(StrictConfigModel):
    """Static and animated image assets for one avatar."""

    standard: NonEmptyStr
    animations: list[AvatarAnimationConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_images(self) -> Self:
        animation_keys = [animation.key for animation in self.animations]
        if len(animation_keys) != len(set(animation_keys)):
            raise ValueError("Animation keys must be unique within one avatar.")
        if "standard" in animation_keys:
            raise ValueError("Animation key 'standard' is reserved.")

        required_keys = {"listening", "speaking", "thinking"}
        missing_keys = required_keys.difference(animation_keys)
        if missing_keys:
            missing = ", ".join(sorted(missing_keys))
            raise ValueError(f"Required avatar animations are missing: {missing}")

        return self


class AvatarConfig(StrictConfigModel):
    """One complete avatar profile."""

    key: NonEmptyStr
    persona: NonEmptyStr
    instructions: NonEmptyStr
    base_path: Path
    greeting_audio: NonEmptyStr
    images: AvatarImagesConfig

    @field_validator("base_path", mode="after")
    @classmethod
    def normalize_base_path(cls, value: Path) -> Path:
        return _resolve_runtime_path(value)

    @model_validator(mode="after")
    def validate_assets(self) -> Self:
        if not self.base_path.is_dir():
            raise ValueError(
                f"Avatar base_path is missing or not a directory: {self.base_path}"
            )

        resolve_avatar_asset_path(self.base_path, self.images.standard)
        for animation in self.images.animations:
            resolve_avatar_asset_path(
                self.base_path,
                animation.sprite_set,
            )

        return self


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


class UserConfig(StrictConfigModel):
    """Validated editable Avalo configuration."""

    name: NonEmptyStr
    tts: TtsUserConfig
    avatars: list[AvatarConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_avatars(self) -> Self:
        avatar_keys = [avatar.key for avatar in self.avatars]
        if len(avatar_keys) != len(set(avatar_keys)):
            raise ValueError("Avatar keys must be unique.")
        if "standard" not in avatar_keys:
            raise ValueError("Required avatar 'standard' is missing.")
        return self

    @property
    def standard_avatar(self) -> AvatarConfig:
        """Return the uniquely validated standard avatar."""
        return next(avatar for avatar in self.avatars if avatar.key == "standard")


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
