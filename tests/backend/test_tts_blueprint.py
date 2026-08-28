import pytest

from app.tts.chatterbox import ChatterboxTextToSpeech


@pytest.mark.anyio
async def test_chatterbox_tts_blueprint_is_not_implemented():
    tts = ChatterboxTextToSpeech()

    with pytest.raises(NotImplementedError):
        await tts.synthesize("Hallo")
