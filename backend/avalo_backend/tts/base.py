"""Runtime-independent text-to-speech contract."""

from pathlib import Path
from typing import Protocol


class TextToSpeech(Protocol):
    """Synthesize local speech from a completed response."""

    async def synthesize(self, text: str) -> Path:
        """Create an audio file and return its local path."""
        ...

