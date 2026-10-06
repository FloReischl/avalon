from app.state import AvalonState


class AvatarCommand:
    """Select the process-local current avatar."""

    key = "avatar set"

    def __init__(self, state: AvalonState) -> None:
        self._state = state

    def get_help(self) -> str:
        avatars = "\n".join(f"  {avatar.key}" for avatar in self._state.avatars)
        if not avatars:
            avatars = "  (none)"
        return (
            "/avatar set <avatar>\n\n"
            "Changes the avatar theme.\n\n"
            f"Available avatars:\n{avatars}"
        )

    async def execute(
        self,
        payload: str,
        context=None,
    ) -> str:
        del context

        if not self._state.set_current_avatar(payload):
            return "invalid avatar key"

        return "ok"
