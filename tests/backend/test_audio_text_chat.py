"""Tests for sequential STT-to-text audio orchestration."""

import pytest

from app.services.audio_text_chat import AudioTurnError


def test_empty_transcript_is_a_defined_audio_turn_error() -> None:
    error = AudioTurnError("Keine Sprache erkannt")

    assert str(error) == "Keine Sprache erkannt"