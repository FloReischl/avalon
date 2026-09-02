"""Text-chat application service."""

from collections.abc import AsyncIterator

from app.runtime.base import ModelRuntime


class ChatService:
    """Coordinate text-chat generation independently of HTTP and runtime details."""

    def __init__(self, runtime: ModelRuntime) -> None:
        self._runtime = runtime

    def stream_response(self, message: str) -> AsyncIterator[str]:
        """Stream a response for one text-chat input."""
        return self._runtime.generate_text_stream(message)
