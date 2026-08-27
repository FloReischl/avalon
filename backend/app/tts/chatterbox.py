"""Planned Chatterbox Multilingual adapter."""

from pathlib import Path


class ChatterboxTextToSpeech:
    """Stub for the TTS candidate selected in ADR 007."""

    async def synthesize(self, text: str) -> Path:
        del text
        raise NotImplementedError("Chatterbox TTS is not implemented yet.")

