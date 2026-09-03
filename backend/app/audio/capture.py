"""Backend-local microphone capture through PipeWire."""

import asyncio
import os
import signal
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.config import settings


class CaptureError(RuntimeError):
    """Raised when a microphone recording cannot be produced."""


@dataclass(frozen=True, slots=True)
class CapturedAudio:
    """Metadata for an unnormalized microphone recording."""

    path: Path
    duration_seconds: float
    sample_rate_hz: int
    channels: int


class CaptureProcess(Protocol):
    """Subset of an asyncio subprocess used by the recorder."""

    returncode: int | None

    def send_signal(self, signal_number: int) -> None: ...

    def kill(self) -> None: ...

    async def communicate(self) -> tuple[bytes | None, bytes | None]: ...


class PipeWireRecorder:
    """Manage one push-to-talk recording through ``pw-record``."""

    def __init__(
        self,
        *,
        max_duration_seconds: float = settings.audio_max_seconds,
        output_directory: Path | None = None,
    ) -> None:
        if max_duration_seconds <= 0:
            raise ValueError("max_duration_seconds must be positive")

        self._max_duration_seconds = max_duration_seconds
        self._output_directory = output_directory
        self._process: CaptureProcess | None = None
        self._path: Path | None = None
        self._timeout_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    @property
    def is_recording(self) -> bool:
        """Return whether a capture process is currently owned."""
        return self._process is not None

    async def start(self) -> None:
        """Start recording in PipeWire's default capture format."""
        async with self._lock:
            if self._process is not None:
                raise CaptureError("A recording is already active.")

            file_descriptor, temporary_name = tempfile.mkstemp(
                prefix="avalo-recording-",
                suffix=".wav",
                dir=self._output_directory,
            )
            os.close(file_descriptor)
            path = Path(temporary_name)
            path.unlink()

            try:
                process = await asyncio.create_subprocess_exec(
                    "pw-record",
                    str(path),
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE,
                )
            except (FileNotFoundError, OSError) as exc:
                path.unlink(missing_ok=True)
                raise CaptureError(f"Could not start pw-record: {exc}") from exc

            self._process = process
            self._path = path
            self._timeout_task = asyncio.create_task(self._abort_after_limit())

    async def stop(self) -> CapturedAudio:
        """Stop and return a valid, still unnormalized WAV recording."""
        async with self._lock:
            process, path = self._take_active_recording()
            self._cancel_timeout()

        was_running = process.returncode is None
        _, stderr = await self._finish_process(process)
        expected_exit = process.returncode in (0, -signal.SIGINT) or (
            was_running and process.returncode == 1
        )
        if not expected_exit:
            path.unlink(missing_ok=True)
            detail = (stderr or b"").decode(errors="replace").strip()
            raise CaptureError(f"pw-record failed: {detail or process.returncode}")

        try:
            return inspect_wav(path)
        except CaptureError:
            path.unlink(missing_ok=True)
            raise

    async def abort(self) -> None:
        """Stop and discard the active recording."""
        async with self._lock:
            if self._process is None or self._path is None:
                return
            process, path = self._take_active_recording()
            self._cancel_timeout()

        await self._finish_process(process)
        path.unlink(missing_ok=True)

    def _take_active_recording(self) -> tuple[CaptureProcess, Path]:
        if self._process is None or self._path is None:
            raise CaptureError("No recording is active.")
        process = self._process
        path = self._path
        self._process = None
        self._path = None
        return process, path

    def _cancel_timeout(self) -> None:
        timeout_task = self._timeout_task
        self._timeout_task = None
        if timeout_task is not None and timeout_task is not asyncio.current_task():
            timeout_task.cancel()

    async def _abort_after_limit(self) -> None:
        try:
            await asyncio.sleep(self._max_duration_seconds)
            await self.abort()
        except asyncio.CancelledError:
            pass

    @staticmethod
    async def _finish_process(
        process: CaptureProcess,
    ) -> tuple[bytes | None, bytes | None]:
        if process.returncode is None:
            process.send_signal(signal.SIGINT)
        try:
            return await asyncio.wait_for(process.communicate(), timeout=2.0)
        except TimeoutError:
            process.kill()
            return await process.communicate()


def inspect_wav(path: Path) -> CapturedAudio:
    """Read capture metadata without applying normalization."""
    try:
        with wave.open(str(path), "rb") as recording:
            frames = recording.getnframes()
            sample_rate_hz = recording.getframerate()
            channels = recording.getnchannels()
    except (OSError, EOFError, wave.Error) as exc:
        raise CaptureError("pw-record did not produce a valid WAV file.") from exc

    if frames <= 0 or sample_rate_hz <= 0 or channels <= 0:
        raise CaptureError("pw-record produced an empty WAV file.")

    return CapturedAudio(
        path=path,
        duration_seconds=frames / sample_rate_hz,
        sample_rate_hz=sample_rate_hz,
        channels=channels,
    )
