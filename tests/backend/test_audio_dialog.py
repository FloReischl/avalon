"""Capture-dialog tests."""

from array import array

from app.audio.capture import _DialogTurnBuffer


def pcm(amplitude: int, samples: int) -> bytes:
    return array("h", [amplitude] * samples).tobytes()


def test_dialog_turn_waits_for_speech_and_stops_after_silence() -> None:
    buffer = _DialogTurnBuffer(
        sample_rate_hz=10,
        silence_seconds=3,
        speech_threshold=0.01,
    )

    assert not buffer.add_chunk(pcm(0, 20))
    assert not buffer.add_chunk(pcm(1000, 10))
    assert not buffer.add_chunk(pcm(0, 20))
    assert buffer.add_chunk(pcm(0, 10))
    assert buffer.pcm == pcm(1000, 10)


def test_dialog_turn_preserves_short_pause_when_speech_resumes() -> None:
    buffer = _DialogTurnBuffer(
        sample_rate_hz=10,
        silence_seconds=3,
        speech_threshold=0.01,
    )

    assert not buffer.add_chunk(pcm(1000, 10))
    assert not buffer.add_chunk(pcm(0, 20))
    assert not buffer.add_chunk(pcm(1000, 10))
    assert buffer.add_chunk(pcm(0, 30))
    assert buffer.pcm == (
        pcm(1000, 10)
        + pcm(0, 20)
        + pcm(1000, 10)
    )


def test_dialog_turn_does_not_end_during_long_speech() -> None:
    buffer = _DialogTurnBuffer(
        sample_rate_hz=10,
        silence_seconds=3,
        speech_threshold=0.01,
    )

    assert not buffer.add_chunk(pcm(1000, 40))
    assert buffer.pcm == pcm(1000, 40)