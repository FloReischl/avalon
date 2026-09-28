"""Editable per-user Avalon avatar configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AVATARS_CONFIG_PATH = Path("~/.avalon/avatars.yaml").expanduser()

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


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
        raise ValueError(f"Avatar asset resolves outside base_path {base_path}: {asset}")
    if not resolved.is_file():
        raise ValueError(f"Avatar asset is missing: {resolved}")
    return resolved


class StrictAvatarsConfigModel(BaseModel):
    """Reject unknown avatar configuration fields."""

    model_config = ConfigDict(extra="forbid")


class SpriteRegion(StrictAvatarsConfigModel):
    x: int = Field(ge=0, strict=True)
    y: int = Field(ge=0, strict=True)
    width: int = Field(gt=0, strict=True)
    height: int = Field(gt=0, strict=True)

    @model_validator(mode="before")
    @classmethod
    def parse_compact_region(cls, value: object) -> object:
        if isinstance(value, (list, tuple)):
            if len(value) != 4:
                raise ValueError("Sprite region must contain exactly x, y, width, height.")
            return {"x": value[0], "y": value[1], "width": value[2], "height": value[3]}
        return value


class AvatarAnimationConfig(StrictAvatarsConfigModel):
    key: NonEmptyStr
    category: NonEmptyStr
    sprite_set: NonEmptyStr = Field(alias="sprite-set")
    sprites: list[SpriteRegion] = Field(min_length=1)


class AvatarImagesConfig(StrictAvatarsConfigModel):
    standard: NonEmptyStr
    animations: list[AvatarAnimationConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_images(self) -> Self:
        animation_keys = [animation.key for animation in self.animations]
        if len(animation_keys) != len(set(animation_keys)):
            raise ValueError("Animation keys must be unique within one avatar.")
        if "standard" in animation_keys:
            raise ValueError("Animation key 'standard' is reserved.")
        missing_keys = {"listening", "speaking", "thinking"}.difference(animation_keys)
        if missing_keys:
            raise ValueError(f"Required avatar animations are missing: {', '.join(sorted(missing_keys))}")
        return self


class AvatarConfig(StrictAvatarsConfigModel):
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
            raise ValueError(f"Avatar base_path is missing or not a directory: {self.base_path}")
        resolve_avatar_asset_path(self.base_path, self.images.standard)
        for animation in self.images.animations:
            resolve_avatar_asset_path(self.base_path, animation.sprite_set)
        return self


class AvatarsConfig(StrictAvatarsConfigModel):
    """Validated editable avatar catalog."""

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
        return next(avatar for avatar in self.avatars if avatar.key == "standard")


_avatars_config: AvatarsConfig | None = None


def load_avatars_config(path: Path = AVATARS_CONFIG_PATH) -> AvatarsConfig:
    """Load and fully validate one avatar configuration file."""
    return AvatarsConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def initialize_avatars_config(path: Path = AVATARS_CONFIG_PATH) -> AvatarsConfig:
    """Load the process-local avatar configuration exactly once."""
    global _avatars_config
    if _avatars_config is None:
        _avatars_config = load_avatars_config(path)
    return _avatars_config


def get_avatars_config() -> AvatarsConfig:
    """Return the initialized process-local avatar configuration."""
    if _avatars_config is None:
        raise RuntimeError("Avatar configuration has not been initialized.")
    return _avatars_config
