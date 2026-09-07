"""Runtime-independent text-to-speech contract."""

from typing import Protocol


class TextToSpeech(Protocol):
    """Synthesize local speech from a completed response."""

    async def synthesize(self, text: str) -> bytes:
        """Return synthesized speech as WAV bytes."""
        ...

    async def unload(self) -> None:
        """Release resources held by the TTS engine."""
        ...


