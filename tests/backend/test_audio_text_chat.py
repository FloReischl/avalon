"""Tests for streaming Whisper-to-text orchestration."""

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.audio.capture import CapturedAudio
from app.services.audio_text_chat import (
    AudioTextChatService,
    AudioTurnError,
    _StreamingTranscription,
)
from app.stt.whisper import AudioChunk


class FakeStt:
    def __init__(self, responses=None, error=None) -> None:
        self.responses = responses or {}
        self.error = error
        self.calls: list[Path] = []
        self.active = self.maximum_active = 0

    async def transcribe(self, path: Path) -> str:
        self.calls.append(path)
        self.active += 1
        self.maximum_active = max(self.maximum_active, self.active)
        try:
            await asyncio.sleep(0)
            if self.error is not None:
                raise self.error
            return self.responses[path.name]
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
    def __init__(self, captured: CapturedAudio | None = None) -> None:
        self.captured = captured
        self.started = self.aborted = False
        self.chunk_sink = None

    async def start(self, chunk_sink) -> None:
        self.started = True
        self.chunk_sink = chunk_sink

    async def stop(self) -> CapturedAudio:
        assert self.captured is not None
        return self.captured

    async def abort(self) -> None:
        self.aborted = True


class FakeRuntime:
    def __init__(self) -> None:
        self.contexts: list[list[dict[str, str]]] = []

    def generate_text_stream(self, messages):
        self.contexts.append(messages)

        async def generate():
            yield "Ant"
            yield "wort"

        return generate()


class FakeRepository:
    def __init__(self) -> None:
        self.created: list[tuple[str, str, str]] = []
        self.messages: list[tuple[int, str, str]] = []

    def create_chat_with_message(self, title, role, content):
        self.created.append((title, role, content))
        return SimpleNamespace(id=7)

    def add_message(self, chat_id, role, content) -> None:
        self.messages.append((chat_id, role, content))


class FakeCompressionService:
    async def compress_if_needed(self, chat_id: int) -> None:
        del chat_id


def chunk(name: str) -> AudioChunk:
    return AudioChunk(Path(name), 0.0, 10.0)


def captured(tmp_path: Path) -> CapturedAudio:
    path = tmp_path / "recording.wav"
    path.write_bytes(b"temporary wav")
    directory = tmp_path / "chunks"
    directory.mkdir()
    (directory / "whisper-chunk-000.wav").write_bytes(b"chunk")
    return CapturedAudio(path, 10.0, 16_000, 1, directory)


def test_empty_transcript_is_a_defined_audio_turn_error() -> None:
    assert str(AudioTurnError("Keine Sprache erkannt")) == "Keine Sprache erkannt"


@pytest.mark.asyncio
async def test_streaming_transcription_merges_serially() -> None:
    stt = FakeStt({
        "first.wav": "Hallo Welt,",
        "second.wav": "welt, das ist Avalo",
    })
    transcription = _StreamingTranscription(stt, asyncio.Queue())
    transcription.start()
    await transcription.enqueue(chunk("first.wav"))
    await transcription.enqueue(chunk("second.wav"))

    assert await transcription.finish() == "Hallo Welt, das ist Avalo"
    assert [path.name for path in stt.calls] == ["first.wav", "second.wav"]
    assert stt.maximum_active == 1


@pytest.mark.asyncio
async def test_chunk_failure_fails_the_complete_turn() -> None:
    transcription = _StreamingTranscription(
        FakeStt(error=RuntimeError("Whisper unavailable")),
        asyncio.Queue(),
    )
    transcription.start()
    await transcription.enqueue(chunk("failed.wav"))

    with pytest.raises(AudioTurnError, match="fehlgeschlagen"):
        await transcription.finish()


@pytest.mark.asyncio
async def test_finish_times_out_when_the_queue_cannot_drain(monkeypatch) -> None:
    stt = BlockingStt()
    transcription = _StreamingTranscription(stt, asyncio.Queue())
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
    service = AudioTextChatService(recorder, object(), stt=BlockingStt())

    await service.start_recording()

    assert recorder.started is True
    assert recorder.chunk_sink is not None
    await service.abort_recording()
    assert recorder.aborted is True


@pytest.mark.asyncio
async def test_chunk_failure_never_calls_llm_or_persists(tmp_path: Path) -> None:
    recorder = FakeRecorder(captured(tmp_path))
    runtime = FakeRuntime()
    repository = FakeRepository()
    service = AudioTextChatService(
        recorder,
        runtime,
        repository,
        stt=FakeStt(error=RuntimeError("Whisper unavailable")),
    )

    await service.start_recording()
    await recorder.chunk_sink(chunk("failed.wav"))

    with pytest.raises(AudioTurnError, match="fehlgeschlagen"):
        async for _event in service.stream_response_with_transcription([]):
            pass

    assert runtime.contexts == []
    assert repository.created == []
    assert repository.messages == []


@pytest.mark.asyncio
async def test_final_transcript_precedes_llm_and_persistence(tmp_path: Path) -> None:
    recorder = FakeRecorder(captured(tmp_path))
    runtime = FakeRuntime()
    repository = FakeRepository()
    service = AudioTextChatService(
        recorder,
        runtime,
        repository,
        compression_service=FakeCompressionService(),
        stt=FakeStt({"final.wav": "Mein finaler Text"}),
    )

    await service.start_recording()
    await recorder.chunk_sink(chunk("final.wav"))
    events = [
        event
        async for event in service.stream_response_with_transcription([])
    ]

    assert [(event.kind, event.text) for event in events] == [
        ("transcript", "Mein finaler Text"),
        ("chat", "7"),
        ("assistant", "Ant"),
        ("assistant", "wort"),
        ("assistant_done", ""),
    ]
    assert repository.created[0][1:] == ("user", "Mein finaler Text")
    assert repository.messages == [(7, "assistant", "Antwort")]
    assert runtime.contexts == [
        [{"role": "user", "content": "Mein finaler Text"}],
    ]

    for _ in range(20):
        if not (
            (tmp_path / "recording.wav").exists()
            or (tmp_path / "chunks").exists()
        ):
            break
        await asyncio.sleep(0.01)

    assert not (tmp_path / "recording.wav").exists()
    assert not (tmp_path / "chunks").exists()