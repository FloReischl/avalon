"""Tests for streaming Whisper-to-text orchestration."""

import asyncio
from pathlib import Path

import pytest

from app.services.audio_text_chat import (
    AudioTextChatService,
    AudioTurnError,
    _StreamingTranscription,
)
from app.stt.whisper import AudioChunk


class FakeStt:
    def __init__(
        self,
        responses: dict[str, str] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._responses = responses or {}
        self._error = error
        self.calls: list[Path] = []
        self.active = 0
        self.maximum_active = 0

    async def transcribe(self, path: Path) -> str:
        self.calls.append(path)
        self.active += 1
        self.maximum_active = max(self.maximum_active, self.active)
        try:
            await asyncio.sleep(0)
            if self._error is not None:
                raise self._error
            return self._responses[path.name]
        finally:
            self.active -= 1


class BlockingStt(FakeStt):
    def __init__(self) -> None:
        super().__init__()
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def transcribe(self, path: Path) -> str:
        del path
        self.entered.set()
        await self.release.wait()
        return "Text"


class FakeRecorder:
    def __init__(self) -> None:
        self.started = False
        self.aborted = False
        self.chunk_sink = None

    async def start(self, chunk_sink) -> None:
        self.started = True
        self.chunk_sink = chunk_sink

    async def abort(self) -> None:
        self.aborted = True


def chunk(name: str) -> AudioChunk:
    return AudioChunk(
        path=Path(name),
        start_seconds=0.0,
        end_seconds=10.0,
    )


def test_empty_transcript_is_a_defined_audio_turn_error() -> None:
    error = AudioTurnError("Keine Sprache erkannt")

    assert str(error) == "Keine Sprache erkannt"


@pytest.mark.asyncio
async def test_streaming_transcription_merges_serially() -> None:
    stt = FakeStt(
        {
            "first.wav": "Hallo Welt,",
            "second.wav": "welt, das ist Avalo",
        }
    )
    transcription = _StreamingTranscription(
        stt=stt,
        queue=asyncio.Queue(),
    )
    transcription.start()

    await transcription.enqueue(chunk("first.wav"))
    await transcription.enqueue(chunk("second.wav"))

    assert await transcription.finish() == "Hallo Welt, das ist Avalo"
    assert [path.name for path in stt.calls] == [
        "first.wav",
        "second.wav",
    ]
    assert stt.maximum_active == 1


@pytest.mark.asyncio
async def test_chunk_failure_fails_the_complete_turn() -> None:
    transcription = _StreamingTranscription(
        stt=FakeStt(error=RuntimeError("Whisper unavailable")),
        queue=asyncio.Queue(),
    )
    transcription.start()
    await transcription.enqueue(chunk("failed.wav"))

    with pytest.raises(AudioTurnError, match="fehlgeschlagen"):
        await transcription.finish()


@pytest.mark.asyncio
async def test_finish_times_out_when_the_queue_cannot_drain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stt = BlockingStt()
    transcription = _StreamingTranscription(
        stt=stt,
        queue=asyncio.Queue(),
    )
    transcription.start()
    await transcription.enqueue(chunk("blocked.wav"))
    await stt.entered.wait()
    monkeypatch.setattr(
        "app.services.audio_text_chat.STT_COMPLETION_TIMEOUT_SECONDS",
        0.01,
    )

    with pytest.raises(AudioTurnError, match="abgelaufen"):
        await transcription.finish()

    await transcription.cancel()


@pytest.mark.asyncio
async def test_ptt_starts_capture_without_waiting_for_whisper() -> None:
    recorder = FakeRecorder()
    service = AudioTextChatService(
        recorder=recorder,
        runtime=object(),
        stt=BlockingStt(),
    )

    await service.start_recording()

    assert recorder.started is True
    assert recorder.chunk_sink is not None

    await service.abort_recording()

    assert recorder.aborted is True