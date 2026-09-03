"""Tests for backend-local audio capture process control."""

import asyncio
import shutil
import signal
from pathlib import Path

import pytest

from app.audio.capture import CaptureError, PipeWireRecorder


class FakeCaptureProcess:
    def __init__(self, output: Path, source: Path) -> None:
        self.returncode: int | None = None
        self._output = output
        self._source = source
        self.signals: list[int] = []

    def send_signal(self, signal_number: int) -> None:
        self.signals.append(signal_number)
        shutil.copyfile(self._source, self._output)
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
            Path(command[-1]),
            Path("tests/data/german-transcription.wav"),
        )
        processes.append(process)
        return process

    monkeypatch.setattr(
        "app.audio.capture.asyncio.create_subprocess_exec",
        create_subprocess_exec,
    )
    return processes, commands


@pytest.mark.asyncio
async def test_stop_returns_unnormalized_wav_metadata(
    tmp_path: Path,
    fake_pw_record,
) -> None:
    processes, commands = fake_pw_record
    recorder = PipeWireRecorder(output_directory=tmp_path)

    await recorder.start()
    capture = await recorder.stop()

    assert commands[0][:1] == ("pw-record",)
    assert capture.path.is_file()
    assert capture.duration_seconds == pytest.approx(4.6248125)
    assert capture.sample_rate_hz == 16_000
    assert capture.channels == 1
    assert processes[0].signals == [signal.SIGINT]
    assert recorder.is_recording is False


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
            Path(command[-1]),
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
async def test_duration_limit_aborts_and_discards_recording(
    tmp_path: Path,
    fake_pw_record,
) -> None:
    recorder = PipeWireRecorder(
        max_duration_seconds=0.01,
        output_directory=tmp_path,
    )

    await recorder.start()
    await asyncio.sleep(0.03)

    assert list(tmp_path.iterdir()) == []
    assert recorder.is_recording is False


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
async def test_invalid_wav_is_rejected_and_removed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class InvalidWavProcess(FakeCaptureProcess):
        def send_signal(self, signal_number: int) -> None:
            self.signals.append(signal_number)
            self._output.write_bytes(b"not a wav")
            self.returncode = -signal_number

    async def create_subprocess_exec(*command, **kwargs):
        return InvalidWavProcess(
            Path(command[-1]),
            Path("tests/data/german-transcription.wav"),
        )

    monkeypatch.setattr(
        "app.audio.capture.asyncio.create_subprocess_exec",
        create_subprocess_exec,
    )
    recorder = PipeWireRecorder(output_directory=tmp_path)
    await recorder.start()

    with pytest.raises(CaptureError, match="valid WAV"):
        await recorder.stop()

    assert list(tmp_path.iterdir()) == []
