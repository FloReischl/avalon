"""Process-local state for Avalo's single avatar audio call."""

from dataclasses import dataclass


class AudioCallAlreadyActiveError(RuntimeError):
    """Raised when a second call is started while one is already active."""


@dataclass(frozen=True)
class AudioCallStatus:
    """The frontend-visible state of the one active audio call."""

    active: bool
    chat_id: int | None
    turn_active: bool
    pending_speech: str | None = None


class AudioCallState:
    """Own the state of Avalo's one process-local avatar call.

    The avatar remains responsible for driving the call.  This object is only
    the backend source of truth that other frontend windows can query.
    """

    def __init__(self) -> None:
        self._active = False
        self._chat_id: int | None = None
        self._turn_active = False
        self._pending_speech: str | None = None

    def get_status(self) -> AudioCallStatus:
        return AudioCallStatus(
            active=self._active,
            chat_id=self._chat_id,
            turn_active=self._turn_active,
            pending_speech=self._pending_speech,
        )

    def start(self, chat_id: int | None = None) -> AudioCallStatus:
        if self._active:
            raise AudioCallAlreadyActiveError("An audio call is already active.")

        self._active = True
        self._chat_id = chat_id
        self._turn_active = False
        return self.get_status()

    def bind_chat(self, chat_id: int) -> AudioCallStatus:
        if not self._active:
            raise RuntimeError("Cannot bind a chat without an active audio call.")

        if self._chat_id is not None and self._chat_id != chat_id:
            raise RuntimeError("The active audio call is already bound to another chat.")

        self._chat_id = chat_id
        return self.get_status()

    def set_turn_active(self, active: bool) -> AudioCallStatus:
        if not self._active:
            raise RuntimeError("Cannot update a turn without an active audio call.")

        self._turn_active = active
        return self.get_status()

    def end(self) -> AudioCallStatus:
        self._active = False
        self._chat_id = None
        self._turn_active = False
        self._pending_speech = None
        return self.get_status()

    def queue_speech(self, text: str) -> None:
        if self._active and text:
            self._pending_speech = text

    def consume_speech(self) -> str | None:
        text = self._pending_speech
        self._pending_speech = None
        return text
