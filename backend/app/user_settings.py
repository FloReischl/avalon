"""Editable per-user Avalon user settings (e.g. avatar zoom)."""

from __future__ import annotations

from pathlib import Path
import sys
import yaml
import logging
from pydantic import BaseModel, Field, model_validator
from typing import Self

logger = logging.getLogger(__name__)

USER_SETTINGS_PATH = Path("~/.avalon/user-settings.yaml").expanduser()


class UserSettings(BaseModel):
    """Validated user settings."""

    avatar_zoom: float = Field(default=1.0, ge=0.5, le=1.5)


def load_user_settings(path: Path = USER_SETTINGS_PATH) -> UserSettings:
    """Load and fully validate one user settings file."""
    if not path.is_file():
        return UserSettings(avatar_zoom=1.0)

    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
    except Exception as e:
        logger.exception("Error parsing user settings file %s: %s", path, e)
        sys.exit(1)

    if data is None:
        return UserSettings(avatar_zoom=1.0)

    if not isinstance(data, dict):
        logger.error("Error: user settings file %s must contain a mapping.", path)
        sys.exit(1)

    zoom_val = data.get("avatar_zoom", 1.0)
    if zoom_val is None:
        zoom_val = 1.0

    if not isinstance(zoom_val, (int, float)) or isinstance(zoom_val, bool):
        logger.error(
            "Error: avatar_zoom in %s must be a number between 0.5 and 1.5, got %r",
            path,
            zoom_val,
        )
        sys.exit(1)

    zoom = float(zoom_val)
    if not (0.5 <= zoom <= 1.5):
        logger.error(
            "Error: avatar_zoom in %s must be between 0.5 and 1.5, got %s",
            path,
            zoom,
        )
        sys.exit(1)

    return UserSettings(avatar_zoom=zoom)


def save_user_settings(avatar_zoom: float, path: Path | None = None) -> UserSettings:
    """Persist avatar_zoom while preserving other existing user settings."""
    target_path = path if path is not None else USER_SETTINGS_PATH
    if not (0.5 <= avatar_zoom <= 1.5):
        raise ValueError(f"avatar_zoom must be between 0.5 and 1.5, got {avatar_zoom}")

    extra = {}
    if target_path.is_file():
        raw = target_path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        if data is not None:
            if not isinstance(data, dict):
                raise ValueError(f"User settings file {target_path} must contain a mapping.")
            extra = dict(data)

    extra["avatar_zoom"] = float(avatar_zoom)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(yaml.safe_dump(extra, sort_keys=False), encoding="utf-8")

    global _user_settings
    _user_settings = UserSettings(avatar_zoom=float(avatar_zoom))
    return _user_settings


_user_settings: UserSettings | None = None


def initialize_user_settings(path: Path = USER_SETTINGS_PATH) -> UserSettings:
    """Load the process-local user settings exactly once."""
    global _user_settings

    if _user_settings is None:
        _user_settings = load_user_settings(path)
    return _user_settings


def get_user_settings() -> UserSettings:
    """Return the initialized process-local user settings."""
    global _user_settings
    if _user_settings is None:
        _user_settings = load_user_settings()
    return _user_settings
