import asyncio
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

    async def transcribe_audio_stream(
        self,
        audio_file: Path,
    ):
        yield "Transkript"


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


class FakeParallelRecorder:
    def __init__(self, captured: CapturedAudio) -> None:
        self.captured = captured

    async def stop(self) -> CapturedAudio:
        return self.captured


class FakeParallelRuntime:
    def __init__(self) -> None:
        self.assistant_started = asyncio.Event()
        self.transcript_started = asyncio.Event()
        self.assistant_path: Path | None = None
        self.transcript_path: Path | None = None

    async def generate_from_audio_stream(
        self,
        audio_file: Path,
        messages: list[dict[str, str]],
    ):
        self.assistant_path = audio_file
        self.assistant_started.set()
        await self.transcript_started.wait()
        yield "Antwort"

    async def transcribe_audio_stream(
        self,
        audio_file: Path,
    ):
        self.transcript_path = audio_file
        self.transcript_started.set()
        await self.assistant_started.wait()
        yield "Hallo Flo"


@pytest.mark.asyncio
async def test_audio_service_streams_response_and_transcript_from_same_capture(
    tmp_path: Path,
) -> None:
    path = tmp_path / "audio.wav"
    path.write_bytes(b"test")

    captured = CapturedAudio(
        path=path,
        duration_seconds=1.0,
        sample_rate_hz=16000,
        channels=1,
    )
    recorder = FakeParallelRecorder(captured)
    runtime = FakeParallelRuntime()
    service = AudioChatService(recorder, runtime)  # type: ignore[arg-type]

    events = [
        event
        async for event in service.stream_response_with_transcription([])
    ]

    assert {(event.kind, event.text) for event in events} == {
        ("assistant", "Antwort"),
        ("assistant_done", ""),
        ("transcript", "Hallo Flo"),
        ("transcript_done", ""),
    }
    assert runtime.assistant_path == path
    assert runtime.transcript_path == path
    assert not path.exists()


class FakeFailingTranscriptRuntime(FakeParallelRuntime):
    async def transcribe_audio_stream(
        self,
        audio_file: Path,
    ):
        self.transcript_path = audio_file
        self.transcript_started.set()
        await self.assistant_started.wait()
        raise RuntimeError("transcription failed")
        yield


@pytest.mark.asyncio
async def test_audio_service_keeps_response_when_transcription_fails(
    tmp_path: Path,
) -> None:
    path = tmp_path / "audio.wav"
    path.write_bytes(b"test")

    captured = CapturedAudio(
        path=path,
        duration_seconds=1.0,
        sample_rate_hz=16000,
        channels=1,
    )
    recorder = FakeParallelRecorder(captured)
    runtime = FakeFailingTranscriptRuntime()
    service = AudioChatService(recorder, runtime)  # type: ignore[arg-type]

    events = [
        event
        async for event in service.stream_response_with_transcription([])
    ]

    assert ("assistant", "Antwort") in {
        (event.kind, event.text)
        for event in events
    }
    assert any(
        event.kind == "transcript_error"
        for event in events
    )
    assert not any(
        event.kind == "transcript_done"
        for event in events
    )
    assert any(
        event.kind == "assistant_done"
        for event in events
    )
    assert not path.exists()


class FakePersistenceRepository:
    def __init__(self) -> None:
        self.updated_messages: list[tuple[int, str]] = []
        self.added_messages: list[tuple[int, str, str]] = []

    def get_chat(self, chat_id: int):
        return object() if chat_id == 42 else None

    def add_message(
        self,
        chat_id: int,
        role: str,
        content: str,
    ):
        self.added_messages.append((chat_id, role, content))

        class Message:
            id = 7

        return Message()

    def update_message_content(
        self,
        message_id: int,
        content: str,
    ) -> bool:
        self.updated_messages.append((message_id, content))
        return True


class FakeIndependentCompletionRuntime:
    def __init__(self) -> None:
        self.release_assistant = asyncio.Event()

    async def generate_from_audio_stream(
        self,
        audio_file: Path,
        messages: list[dict[str, str]],
    ):
        await self.release_assistant.wait()
        yield "Antwort"

    async def transcribe_audio_stream(
        self,
        audio_file: Path,
    ):
        yield "Hallo Flo"


@pytest.mark.asyncio
async def test_transcript_is_persisted_before_assistant_finishes(
    tmp_path: Path,
) -> None:
    path = tmp_path / "audio.wav"
    path.write_bytes(b"test")

    captured = CapturedAudio(
        path=path,
        duration_seconds=1.0,
        sample_rate_hz=16000,
        channels=1,
    )
    recorder = FakeParallelRecorder(captured)
    runtime = FakeIndependentCompletionRuntime()
    repository = FakePersistenceRepository()
    service = AudioChatService(
        recorder,
        runtime,  # type: ignore[arg-type]
        repository,  # type: ignore[arg-type]
    )

    stream = service.stream_response_with_transcription([], 42)
    iterator = stream.__aiter__()

    while True:
        event = await anext(iterator)
        if event.kind == "transcript_done":
            break

    assert repository.updated_messages == [(7, "Hallo Flo")]
    assert not any(
        role == "assistant"
        for _, role, _ in repository.added_messages
    )

    runtime.release_assistant.set()
    remaining_events = [event async for event in iterator]

    assert any(
        event.kind == "assistant_done"
        for event in remaining_events
    )
    assert (42, "assistant", "Antwort") in repository.added_messages
    assert not path.exists()


class FakePartialTranscriptFailureRuntime:
    async def generate_from_audio_stream(
        self,
        audio_file: Path,
        messages: list[dict[str, str]],
    ):
        yield "Antwort"

    async def transcribe_audio_stream(
        self,
        audio_file: Path,
    ):
        yield "Halb"
        raise RuntimeError("transcription failed")


@pytest.mark.asyncio
async def test_partial_failed_transcript_is_not_persisted(
    tmp_path: Path,
) -> None:
    path = tmp_path / "audio.wav"
    path.write_bytes(b"test")

    captured = CapturedAudio(
        path=path,
        duration_seconds=1.0,
        sample_rate_hz=16000,
        channels=1,
    )
    recorder = FakeParallelRecorder(captured)
    repository = FakePersistenceRepository()
    service = AudioChatService(
        recorder,
        FakePartialTranscriptFailureRuntime(),  # type: ignore[arg-type]
        repository,  # type: ignore[arg-type]
    )

    events = [
        event
        async for event in service.stream_response_with_transcription([], 42)
    ]

    assert repository.updated_messages == []
    assert (42, "assistant", "Antwort") in repository.added_messages
    assert any(
        event.kind == "transcript_error"
        for event in events
    )
    assert not any(
        event.kind == "transcript_done"
        for event in events
    )
    assert not path.exists()