from pathlib import Path

import pytest

from avalo_backend.tts.chatterbox import ChatterboxTextToSpeech


@pytest.mark.skip(reason="TTS implementation follows after the TTS spike.")
async def test_tts_creates_local_audio_file() -> None:
    tts = ChatterboxTextToSpeech()
    output = await tts.synthesize("Guten Tag.")
    assert isinstance(output, Path)
    assert output.exists()

