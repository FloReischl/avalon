"""Tests for backend-local audio capture process control."""

import asyncio
import signal
import wave
from pathlib import Path

import pytest

from app.audio.capture import CaptureError, PipeWireRecorder
from app.config import settings


class FakePcmStream:
    def __init__(self, pcm: bytes) -> None:
        self._pcm = pcm

    async def read(self, size: int) -> bytes:
        await asyncio.sleep(0)
        chunk, self._pcm = self._pcm[:size], self._pcm[size:]
        return chunk


class FakeCaptureProcess:
    def __init__(self, source: Path) -> None:
        self.returncode: int | None = None
        self.signals: list[int] = []
        with wave.open(str(source), "rb") as recording:
            self.stdout = FakePcmStream(recording.readframes(
                recording.getnframes(),
            ))

    def send_signal(self, signal_number: int) -> None:
        self.signals.append(signal_number)
        self.returncode = -signal_number

    def kill(self) -> None:
        self.returncode = -signal.SIGKILL

    async def communicate(self) -> tuple[bytes, bytes]:
        return b"", b""


@pytest.fixture
def fake_pw_record(monkeypatch: pytest.MonkeyPatch):
    processes: list[FakeCaptureProcess] = []
    commands: list[tuple[object, ...]] = []

    async def create_subprocess_exec(*command, **kwargs):
        commands.append(command)
        process = FakeCaptureProcess(
            Path("tests/data/german-transcription.wav"),
        )
        processes.append(process)
        return process

    monkeypatch.setattr(
        "app.audio.capture.asyncio.create_subprocess_exec",
        create_subprocess_exec,
    )
    return processes, commands


def test_recorder_uses_configured_dialog_wait() -> None:
    recorder = PipeWireRecorder()

    assert recorder._dialog_silence_seconds == settings.audio_wait_exceed_seconds


@pytest.mark.asyncio
async def test_stop_returns_unnormalized_wav_metadata(
    tmp_path: Path,
    fake_pw_record,
) -> None:
    processes, commands = fake_pw_record
    recorder = PipeWireRecorder(output_directory=tmp_path)

    await recorder.start()
    capture = await recorder.stop()

    assert commands[0] == (
        "pw-record",
        "--rate=16000",
        "--channels=1",
        "--channel-map=mono",
        "--format=s16",
        "-",
    )
    assert capture.path.is_file()
    assert capture.chunk_directory is not None
    assert capture.chunk_directory.is_dir()


@pytest.mark.asyncio
async def test_full_pcm_window_is_streamed_before_stop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class LongPcmProcess:
        def __init__(self) -> None:
            self.returncode: int | None = None
            self.signals: list[int] = []
            self.stdout = FakePcmStream(b"\1\0" * 160_000)

        def send_signal(self, signal_number: int) -> None:
            self.signals.append(signal_number)
            self.returncode = -signal_number

        def kill(self) -> None:
            self.returncode = -signal.SIGKILL

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"", b""

    async def create_subprocess_exec(*command, **kwargs):
        del command, kwargs
        return LongPcmProcess()

    chunks = []

    async def chunk_sink(chunk) -> None:
        chunks.append(chunk)

    monkeypatch.setattr(
        "app.audio.capture.asyncio.create_subprocess_exec",
        create_subprocess_exec,
    )
    recorder = PipeWireRecorder(output_directory=tmp_path)

    await recorder.start(chunk_sink)
    await asyncio.sleep(0.02)

    assert [(chunk.start_seconds, chunk.end_seconds) for chunk in chunks] == [
        (0.0, 10.0),
    ]
    assert recorder.is_recording is True

    captured = await recorder.stop()

    assert [
        (chunk.start_seconds, chunk.end_seconds) for chunk in chunks
    ] == [
        (0.0, 10.0),
        (8.0, 10.0),
    ]
    assert captured.duration_seconds == pytest.approx(10.0)




@pytest.mark.asyncio
async def test_stop_accepts_pw_record_sigint_exit_code_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class PipeWireSigintProcess(FakeCaptureProcess):
        def send_signal(self, signal_number: int) -> None:
            super().send_signal(signal_number)
            self.returncode = 1

    async def create_subprocess_exec(*command, **kwargs):
        return PipeWireSigintProcess(
            Path("tests/data/german-transcription.wav"),
        )

    monkeypatch.setattr(
        "app.audio.capture.asyncio.create_subprocess_exec",
        create_subprocess_exec,
    )
    recorder = PipeWireRecorder(output_directory=tmp_path)

    await recorder.start()
    capture = await recorder.stop()

    assert capture.path.is_file()


@pytest.mark.asyncio
async def test_abort_discards_recording(
    tmp_path: Path,
    fake_pw_record,
) -> None:
    recorder = PipeWireRecorder(output_directory=tmp_path)

    await recorder.start()
    await recorder.abort()

    assert list(tmp_path.iterdir()) == []
    assert recorder.is_recording is False


@pytest.mark.asyncio
async def test_recording_does_not_auto_abort(
    tmp_path: Path,
    fake_pw_record,
) -> None:
    recorder = PipeWireRecorder(output_directory=tmp_path)

    await recorder.start()
    await asyncio.sleep(0.03)

    assert recorder.is_recording is True
    await recorder.abort()
    assert list(tmp_path.iterdir()) == []



@pytest.mark.asyncio
async def test_concurrent_recording_is_rejected(
    tmp_path: Path,
    fake_pw_record,
) -> None:
    recorder = PipeWireRecorder(output_directory=tmp_path)
    await recorder.start()

    with pytest.raises(CaptureError, match="already active"):
        await recorder.start()

    await recorder.abort()


@pytest.mark.asyncio
async def test_stop_without_recording_is_rejected(tmp_path: Path) -> None:
    recorder = PipeWireRecorder(output_directory=tmp_path)

    with pytest.raises(CaptureError, match="No recording"):
        await recorder.stop()


@pytest.mark.asyncio
async def test_missing_pw_record_is_reported_and_temp_file_is_removed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def missing_pw_record(*command, **kwargs):
        raise FileNotFoundError("pw-record")

    monkeypatch.setattr(
        "app.audio.capture.asyncio.create_subprocess_exec",
        missing_pw_record,
    )
    recorder = PipeWireRecorder(output_directory=tmp_path)

    with pytest.raises(CaptureError, match="Could not start pw-record"):
        await recorder.start()

    assert list(tmp_path.iterdir()) == []
    assert recorder.is_recording is False


@pytest.mark.asyncio
async def test_incomplete_pcm_is_rejected_and_removed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class IncompletePcmProcess(FakeCaptureProcess):
        def __init__(self) -> None:
            self.returncode: int | None = None
            self.signals: list[int] = []
            self.stdout = FakePcmStream(b"\0")

    async def create_subprocess_exec(*command, **kwargs):
        del command, kwargs
        return IncompletePcmProcess()

    monkeypatch.setattr(
        "app.audio.capture.asyncio.create_subprocess_exec",
        create_subprocess_exec,
    )
    recorder = PipeWireRecorder(output_directory=tmp_path)
    await recorder.start()

    with pytest.raises(CaptureError, match="incomplete PCM"):
        await recorder.stop()

    assert list(tmp_path.iterdir()) == []
