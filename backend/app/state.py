from __future__ import annotations

from app.config import LlmConfig, settings
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
        self._current_llm = next(
            llm for llm in settings.llm_models if llm.key == "standard"
        )
        self._llm_inference_count = 0
        self._llm_switch_active = False

    @property
    def user_config(self) -> UserConfig:
        return self._user_config

    @property
    def current_avatar(self) -> AvatarConfig:
        return self._current_avatar

    @property
    def current_llm(self) -> LlmConfig:
        return self._current_llm

    @property
    def llm_inference_active(self) -> bool:
        return self._llm_inference_count > 0

    @property
    def llm_switch_active(self) -> bool:
        return self._llm_switch_active

    def begin_llm_switch(self) -> None:
        if self._llm_switch_active:
            raise RuntimeError("LLM switch is already active.")
        if self.llm_inference_active:
            raise RuntimeError("LLM inference is active.")

        self._llm_switch_active = True

    def end_llm_switch(self) -> None:
        if not self._llm_switch_active:
            raise RuntimeError("LLM switch is not active.")

        self._llm_switch_active = False

    def set_current_llm(self, key: str) -> bool:
        """Select one configured LLM without mutating static configuration."""
        llm = next(
            (
                llm
                for llm in settings.llm_models
                if llm.key == key
            ),
            None,
        )

        if llm is None:
            return False

        self._current_llm = llm
        return True

    def begin_llm_inference(self) -> None:
        self._llm_inference_count += 1

    def end_llm_inference(self) -> None:
        if self._llm_inference_count <= 0:
            raise RuntimeError("LLM inference counter underflow.")
        self._llm_inference_count -= 1

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
