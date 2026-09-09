from array import array
from pathlib import Path

import pytest

from app.audio.capture import CapturedAudio, _DialogTurnBuffer
from app.services.audio_chat import AudioChatService


def pcm(amplitude: int, samples: int) -> bytes:
    return array("h", [amplitude] * samples).tobytes()


def test_dialog_turn_waits_for_speech_and_stops_after_silence() -> None:
    buffer = _DialogTurnBuffer(
        sample_rate_hz=10,
        max_duration_seconds=30,
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
        max_duration_seconds=30,
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


def test_dialog_turn_submits_at_maximum_duration() -> None:
    buffer = _DialogTurnBuffer(
        sample_rate_hz=10,
        max_duration_seconds=3,
        silence_seconds=3,
        speech_threshold=0.01,
    )

    assert buffer.add_chunk(pcm(1000, 40))

    assert buffer.pcm == pcm(1000, 30)


class FakeDialogRecorder:
    def __init__(self, captured: CapturedAudio) -> None:
        self.captured = captured
        self.calls = 0

    async def capture_dialog_turn(self) -> CapturedAudio:
        self.calls += 1
        return self.captured


class FakeRuntime:
    def __init__(self) -> None:
        self.path: Path | None = None
        self.messages: list[dict[str, str]] | None = None

    async def generate_from_audio_stream(
        self,
        audio_file: Path,
        messages: list[dict[str, str]],
    ):
        self.path = audio_file
        self.messages = messages
        yield "Hallo"
        yield " Flo"


@pytest.mark.asyncio
async def test_dialog_service_streams_response_and_removes_capture(
    tmp_path: Path,
) -> None:
    path = tmp_path / "dialog.wav"
    path.write_bytes(b"test")

    captured = CapturedAudio(
        path=path,
        duration_seconds=1.0,
        sample_rate_hz=16000,
        channels=1,
    )
    recorder = FakeDialogRecorder(captured)
    runtime = FakeRuntime()
    service = AudioChatService(recorder, runtime)  # type: ignore[arg-type]
    messages = [{"role": "user", "content": "Vorher"}]

    chunks = [
        chunk
        async for chunk in service.stream_dialog_response(messages)
    ]

    assert chunks == ["Hallo", " Flo"]
    assert recorder.calls == 1
    assert runtime.path == path
    assert runtime.messages == messages
    assert not path.exists()