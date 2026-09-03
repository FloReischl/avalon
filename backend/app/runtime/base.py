"""Runtime-independent model contracts."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol


class ModelRuntime(Protocol):
    """Contract implemented by a local Gemma runtime adapter."""

    async def health(self) -> bool:
        """Return whether the runtime is ready for requests."""
        ...

    async def generate_text(self, message: str) -> str:
        """Generate a complete response from text input."""
        ...

    def generate_text_stream(
        self,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        """Generate response text incrementally from chat context."""
        ...

    async def generate_from_audio(self, audio_file: Path) -> str:
        """Generate a complete response from native audio input."""
        ...

    def generate_from_audio_stream(
        self,
        audio_file: Path,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        """Generate response text incrementally from audio and chat context."""
        ...
