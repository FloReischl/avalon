"""Backend-local microphone capture through PipeWire."""

import asyncio
import math
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


class _DialogTurnBuffer:
    """Detect one speech turn from raw signed 16-bit mono PCM."""

    def __init__(
        self,
        *,
        sample_rate_hz: int,
        max_duration_seconds: float,
        silence_seconds: float,
        speech_threshold: float,
    ) -> None:
        if sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be positive")
        if max_duration_seconds <= 0:
            raise ValueError("max_duration_seconds must be positive")
        if silence_seconds <= 0:
            raise ValueError("silence_seconds must be positive")
        if not 0 < speech_threshold <= 1:
            raise ValueError("speech_threshold must be between 0 and 1")

        self._max_samples = max(
            1,
            round(sample_rate_hz * max_duration_seconds),
        )
        self._silence_limit_samples = max(
            1,
            round(sample_rate_hz * silence_seconds),
        )
        self._speech_threshold = speech_threshold
        self._speech_started = False
        self._total_samples = 0
        self._silence_samples = 0
        self._pcm = bytearray()

    @property
    def pcm(self) -> bytes:
        return bytes(self._pcm)

    def add_chunk(self, pcm: bytes) -> bool:
        """Consume PCM and return whether the current turn is complete."""
        if len(pcm) % 2 != 0:
            raise ValueError("PCM chunk must contain complete 16-bit samples.")

        samples = memoryview(pcm).cast("h")
        if len(samples) == 0:
            return False

        rms = math.sqrt(
            sum(sample * sample for sample in samples) / len(samples),
        ) / 32768.0
        is_speech = rms >= self._speech_threshold

        if not self._speech_started:
            if not is_speech:
                return False
            self._speech_started = True

        sample_count = len(samples)
        self._pcm.extend(pcm)
        self._total_samples += sample_count

        if is_speech:
            self._silence_samples = 0
        else:
            self._silence_samples += sample_count

        if self._silence_samples >= self._silence_limit_samples:
            del self._pcm[-self._silence_samples * 2 :]
            return True

        if self._total_samples >= self._max_samples:
            del self._pcm[self._max_samples * 2 :]
            return True

        return False


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
        dialog_silence_seconds: float = settings.audio_wait_exceed_seconds,
        dialog_speech_threshold: float = 0.015,
        dialog_sample_rate_hz: int = 16000,
    ) -> None:
        if max_duration_seconds <= 0:
            raise ValueError("max_duration_seconds must be positive")
        if dialog_silence_seconds <= 0:
            raise ValueError("dialog_silence_seconds must be positive")
        if not 0 < dialog_speech_threshold <= 1:
            raise ValueError(
                "dialog_speech_threshold must be between 0 and 1",
            )
        if dialog_sample_rate_hz <= 0:
            raise ValueError("dialog_sample_rate_hz must be positive")

        self._max_duration_seconds = max_duration_seconds
        self._output_directory = output_directory
        self._dialog_silence_seconds = dialog_silence_seconds
        self._dialog_speech_threshold = dialog_speech_threshold
        self._dialog_sample_rate_hz = dialog_sample_rate_hz
        self._process: CaptureProcess | None = None
        self._path: Path | None = None
        self._mode: str | None = None
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
            self._mode = "ptt"
            self._timeout_task = asyncio.create_task(self._abort_after_limit())

    async def stop(self) -> CapturedAudio:
        """Stop and return a valid, still unnormalized WAV recording."""
        async with self._lock:
            if self._process is not None and self._mode != "ptt":
                raise CaptureError(
                    "The active recording is not push-to-talk.",
                )
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

    async def capture_dialog_turn(self) -> CapturedAudio:
        """Wait for speech and return one silence- or limit-terminated turn."""
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix="avalo-dialog-",
            suffix=".wav",
            dir=self._output_directory,
        )
        os.close(file_descriptor)
        path = Path(temporary_name)
        path.unlink()

        detector = _DialogTurnBuffer(
            sample_rate_hz=self._dialog_sample_rate_hz,
            max_duration_seconds=self._max_duration_seconds,
            silence_seconds=self._dialog_silence_seconds,
            speech_threshold=self._dialog_speech_threshold,
        )

        async with self._lock:
            if self._process is not None:
                path.unlink(missing_ok=True)
                raise CaptureError("A recording is already active.")

            try:
                process = await asyncio.create_subprocess_exec(
                    "pw-record",
                    f"--rate={self._dialog_sample_rate_hz}",
                    "--channels=1",
                    "--channel-map=mono",
                    "--format=s16",
                    "-",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            except (FileNotFoundError, OSError) as exc:
                path.unlink(missing_ok=True)
                raise CaptureError(
                    f"Could not start pw-record: {exc}",
                ) from exc

            stdout = process.stdout
            if stdout is None:
                process.kill()
                await process.communicate()
                path.unlink(missing_ok=True)
                raise CaptureError("pw-record has no audio output stream.")

            self._process = process
            self._path = path
            self._mode = "dialog"

        process_owned = True

        try:
            bytes_per_chunk = max(
                2,
                round(self._dialog_sample_rate_hz * 0.1) * 2,
            )
            pending = b""

            while True:
                chunk = await stdout.read(bytes_per_chunk)
                if not chunk:
                    async with self._lock:
                        if self._process is not process:
                            raise CaptureError("Dialog recording was aborted.")
                        active_process, active_path = self._take_active_recording()
                        self._cancel_timeout()
                        process_owned = False

                    _, stderr = await active_process.communicate()
                    detail = (stderr or b"").decode(
                        errors="replace",
                    ).strip()
                    active_path.unlink(missing_ok=True)

                    raise CaptureError(
                        "pw-record stopped before a dialog turn was completed: "
                        f"returncode={active_process.returncode}, "
                        f"stderr={detail or '<empty>'}",
                    )

                chunk = pending + chunk
                if len(chunk) % 2:
                    pending = chunk[-1:]
                    chunk = chunk[:-1]
                else:
                    pending = b""

                if chunk and detector.add_chunk(chunk):
                    break

            async with self._lock:
                if self._process is not process:
                    raise CaptureError("Dialog recording was aborted.")
                active_process, active_path = self._take_active_recording()
                self._cancel_timeout()
                process_owned = False

            was_running = active_process.returncode is None
            _, stderr = await self._finish_process(active_process)
            expected_exit = active_process.returncode in (
                0,
                -signal.SIGINT,
            ) or (
                was_running and active_process.returncode == 1
            )
            if not expected_exit:
                detail = (stderr or b"").decode(
                    errors="replace",
                ).strip()
                raise CaptureError(
                    f"pw-record failed: {detail or active_process.returncode}",
                )

            pcm = detector.pcm
            if not pcm:
                raise CaptureError(
                    "Dialog recording produced no speech audio.",
                )

            with wave.open(str(active_path), "wb") as recording:
                recording.setnchannels(1)
                recording.setsampwidth(2)
                recording.setframerate(self._dialog_sample_rate_hz)
                recording.writeframes(pcm)

            return inspect_wav(active_path)
        except BaseException:
            if process_owned:
                await self._discard_if_active(process, path)
            else:
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
        self._mode = None
        return process, path

    async def _discard_if_active(
        self,
        process: CaptureProcess,
        path: Path,
    ) -> None:
        async with self._lock:
            if self._process is not process:
                path.unlink(missing_ok=True)
                return

            active_process, active_path = self._take_active_recording()
            self._cancel_timeout()

        await self._finish_process(active_process)
        active_path.unlink(missing_ok=True)

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
