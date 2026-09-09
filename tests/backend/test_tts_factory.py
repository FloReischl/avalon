"""Tests for configured TTS engine selection."""

import pytest

from app.tts.chatterbox import ChatterboxTextToSpeech
from app.tts.factory import create_tts_engine
from app.tts.kokoro import KokoroTextToSpeech


def test_kokoro_engine_can_be_selected() -> None:
    engine = create_tts_engine("kokoro")

    assert isinstance(engine, KokoroTextToSpeech)


def test_chatterbox_engine_remains_available() -> None:
    engine = create_tts_engine("chatterbox")

    assert isinstance(engine, ChatterboxTextToSpeech)


def test_unknown_engine_fails_with_technical_configuration_error() -> None:
    with pytest.raises(
        RuntimeError,
        match="Unsupported TTS engine configured: 'bogus'",
    ):
        create_tts_engine("bogus")
