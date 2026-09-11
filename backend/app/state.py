from __future__ import annotations

from app.user_config import AvatarConfig, UserConfig
from app.services.audio_call import AudioCallState

_audio_call_state = AudioCallState()

def get_audio_call_state() -> AudioCallState:
    return _audio_call_state


class AvaloState:
    """Process-local mutable runtime state for Avalo."""

    def __init__(self, user_config: UserConfig) -> None:
        self._user_config = user_config
        self._current_avatar = user_config.standard_avatar

    @property
    def user_config(self) -> UserConfig:
        return self._user_config

    @property
    def current_avatar(self) -> AvatarConfig:
        return self._current_avatar

    def set_current_avatar(self, key: str) -> bool:
        """Select one configured avatar without mutating user configuration."""
        avatar = next(
            (
                avatar
                for avatar in self._user_config.avatars
                if avatar.key == key
            ),
            None,
        )

        if avatar is None:
            return False

        self._current_avatar = avatar
        return True


_avalo_state: AvaloState | None = None


def initialize_avalo_state(user_config: UserConfig) -> AvaloState:
    """Initialize process-local Avalo runtime state exactly once."""
    global _avalo_state

    if _avalo_state is None:
        _avalo_state = AvaloState(user_config)

    return _avalo_state


def get_avalo_state() -> AvaloState:
    """Return initialized process-local Avalo runtime state."""
    if _avalo_state is None:
        raise RuntimeError("Avalo state has not been initialized.")

    return _avalo_state
