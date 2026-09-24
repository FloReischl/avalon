from app.state import AvalonState


class AvatarCommand:
    """Select the process-local current avatar."""

    key = "avatar_set"

    def __init__(self, state: AvalonState) -> None:
        self._state = state

    async def execute(self, payload: str) -> str:
        if not self._state.set_current_avatar(payload):
            return "invalid avatar key"

        return "ok"