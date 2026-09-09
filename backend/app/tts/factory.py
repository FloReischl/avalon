"""Configured local text-to-speech engine selection."""

import logging

from app.config import settings
from app.tts.base import TextToSpeech
from app.tts.chatterbox import ChatterboxTextToSpeech
from app.tts.kokoro import KokoroTextToSpeech


logger = logging.getLogger(__name__)


def create_tts_engine(engine_name: str | None = None) -> TextToSpeech:
    """Create the configured process-local TTS engine."""
    selected = engine_name or settings.tts_engine

    if selected == "kokoro":
        return KokoroTextToSpeech()

    if selected == "chatterbox":
        return ChatterboxTextToSpeech()

    message = (
        f"Unsupported TTS engine configured: {selected!r}; "
        "expected 'kokoro' or 'chatterbox'."
    )
    logger.critical(message)
    raise RuntimeError(message)
