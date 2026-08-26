"""Text-chat orchestration boundary."""

from avalo_backend.runtime.base import ModelRuntime


class ChatService:
    """Coordinate an in-memory chat with a model runtime."""

    def __init__(self, runtime: ModelRuntime) -> None:
        self._runtime = runtime

    async def reply(self, message: str) -> str:
        """Generate a complete response for a text message."""

        del message
        raise NotImplementedError("Chat orchestration is not implemented yet.")

