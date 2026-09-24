"""Explicit local GPU integration test for Chatterbox TTS."""

import os

import pytest

from app.tts.chatterbox import ChatterboxTextToSpeech


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("AVALON_RUN_TTS_INTEGRATION") != "1",
        reason="Set AVALON_RUN_TTS_INTEGRATION=1 to run local Chatterbox TTS.",
    ),
]


@pytest.mark.asyncio
async def test_chatterbox_generates_wav_with_selected_reference_voice() -> None:
    tts = ChatterboxTextToSpeech()

    try:
        audio = await tts.synthesize(
            "Hallo Flo. Dies ist der lokale Chatterbox Integrationstest."
        )
    finally:
        await tts.unload()

    assert audio[:4] == b"RIFF"
    assert audio[8:12] == b"WAVE"
