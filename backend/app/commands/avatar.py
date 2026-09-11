from app.state import AvaloState


class AvatarCommand:
    """Select the process-local current avatar."""

    key = "avatar"

    def __init__(self, state: AvaloState) -> None:
        self._state = state

    def execute(self, payload: str) -> str:
        if not self._state.set_current_avatar(payload):
            return "invalid avatar key"

        return "ok"