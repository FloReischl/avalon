"""Audio input preparation contract."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PreparedAudio:
    """Audio normalized for Gemma 4 input."""

    path: Path
    duration_seconds: float
    sample_rate_hz: int = 16_000
    channels: int = 1


class AudioInputPreparer(Protocol):
    """Normalize and validate a push-to-talk recording."""

    async def prepare(self, source: Path) -> PreparedAudio:
        """Prepare one recording with a maximum duration of 30 seconds."""
        ...

