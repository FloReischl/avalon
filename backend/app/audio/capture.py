"""Backend-local microphone capture through PipeWire."""

import asyncio
import math
import os
import signal
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Awaitable, Callable
from typing import Protocol

from app.config import settings
from app.stt.whisper import AudioChunk, StreamingPcmChunker


class CaptureError(RuntimeError):
    """Raised when a microphone recording cannot be produced."""


@dataclass(frozen=True, slots=True)
class CapturedAudio:
    """Metadata for one microphone recording and its transient chunks."""

    path: Path
    duration_seconds: float
    sample_rate_hz: int
    channels: int
    chunk_directory: Path | None = None


class _DialogTurnBuffer:
    """Detect one speech turn from raw signed 16-bit mono PCM."""

    def __init__(
        self,
        *,
        sample_rate_hz: int,
        silence_seconds: float,

        speech_threshold: float,
    ) -> None:
        if sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be positive")
        if silence_seconds <= 0:
            raise ValueError("silence_seconds must be positive")
        if not 0 < speech_threshold <= 1:
            raise ValueError("speech_threshold must be between 0 and 1")

        self._silence_limit_samples = max(
            1,
            round(sample_rate_hz * silence_seconds),
        )
        self._speech_threshold = speech_threshold
        self._speech_started = False
        self._silence_samples = 0
        self._pcm = bytearray()
        self._pending_silence = bytearray()
        self._new_pcm = bytearray()

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

        if is_speech:
            if self._pending_silence:
                self._pcm.extend(self._pending_silence)
                self._new_pcm.extend(self._pending_silence)
                self._pending_silence.clear()
            self._pcm.extend(pcm)
            self._new_pcm.extend(pcm)
            self._silence_samples = 0
            return False

        self._pending_silence.extend(pcm)
        self._silence_samples += len(samples)
        return self._silence_samples >= self._silence_limit_samples

    def take_new_pcm(self) -> bytes:
        """Return accepted PCM not previously handed to the stream."""
        pcm = bytes(self._new_pcm)
        self._new_pcm.clear()
        return pcm


ChunkSink = Callable[[AudioChunk], Awaitable[None]]


@dataclass(slots=True)
class _StreamingCapture:
    """PCM state shared by push-to-talk and dialog capture."""

    pcm: bytearray
    chunker: StreamingPcmChunker
    chunk_sink: ChunkSink | None
    chunk_paths: list[Path]
    chunk_directory: Path


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
        output_directory: Path | None = None,

        dialog_silence_seconds: float = settings.audio_wait_exceed_seconds,
        dialog_speech_threshold: float = 0.015,
        dialog_sample_rate_hz: int = 16000,
    ) -> None:
        if dialog_silence_seconds <= 0:
            raise ValueError("dialog_silence_seconds must be positive")
        if not 0 < dialog_speech_threshold <= 1:
            raise ValueError(
                "dialog_speech_threshold must be between 0 and 1",
            )
        if dialog_sample_rate_hz <= 0:
            raise ValueError("dialog_sample_rate_hz must be positive")

        self._output_directory = output_directory

        self._dialog_silence_seconds = dialog_silence_seconds
        self._dialog_speech_threshold = dialog_speech_threshold
        self._dialog_sample_rate_hz = dialog_sample_rate_hz
        self._process: CaptureProcess | None = None
        self._path: Path | None = None
        self._mode: str | None = None
        self._streaming: _StreamingCapture | None = None
        self._pcm_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    @property
    def is_recording(self) -> bool:
        """Return whether a capture process is currently owned."""
        return self._process is not None

    async def start(self, chunk_sink: ChunkSink | None = None) -> None:
        """Start PTT capture and publish complete Whisper windows immediately."""
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
                raise CaptureError(f"Could not start pw-record: {exc}") from exc

            stdout = process.stdout
            if stdout is None:
                process.kill()
                await process.communicate()
                path.unlink(missing_ok=True)
                raise CaptureError("pw-record has no audio output stream.")

            self._process = process
            self._path = path
            self._mode = "ptt"
            self._start_pcm_stream(
                path=path,
                sample_rate_hz=self._dialog_sample_rate_hz,
                chunk_sink=chunk_sink,
            )
            self._pcm_task = asyncio.create_task(
                self._pump_pcm(stdout),
                name="avalo-ptt-pcm-pump",
            )

    async def stop(self) -> CapturedAudio:
        """Finish PTT capture, publish the tail, and return its full WAV."""
        async with self._lock:
            if self._process is not None and self._mode != "ptt":
                raise CaptureError(
                    "The active recording is not push-to-talk.",
                )
            process, path = self._take_active_recording()
            pcm_task, self._pcm_task = self._pcm_task, None

        was_running = process.returncode is None
        if was_running:
            process.send_signal(signal.SIGINT)

        try:
            if pcm_task is not None:
                await pcm_task
            _, stderr = await self._finish_process(
                process,
                send_sigint=False,
            )
            expected_exit = process.returncode in (0, -signal.SIGINT) or (
                was_running and process.returncode == 1
            )
            if not expected_exit:
                detail = (stderr or b"").decode(errors="replace").strip()
                raise CaptureError(
                    f"pw-record failed: {detail or process.returncode}",
                )

            streaming = self._streaming
            if streaming is None:
                raise CaptureError("PTT PCM stream was lost.")
            self._write_pcm_wav(
                path,
                streaming.pcm,
                self._dialog_sample_rate_hz,
            )
            chunk_directory = streaming.chunk_directory
            await self._finish_pcm_stream()
            return self._with_chunk_directory(path, chunk_directory)
        except BaseException:
            path.unlink(missing_ok=True)
            self._discard_pcm_stream()
            raise

    async def capture_dialog_turn(
        self,
        chunk_sink: ChunkSink | None = None,
    ) -> CapturedAudio:
        """Wait for speech and return one silence-terminated turn."""

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
            self._start_pcm_stream(
                path=path,
                sample_rate_hz=self._dialog_sample_rate_hz,
                chunk_sink=chunk_sink,
            )

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

                if chunk:
                    completed = detector.add_chunk(chunk)
                    accepted_pcm = detector.take_new_pcm()
                    if accepted_pcm:
                        await self._add_pcm(accepted_pcm)
                    if completed:
                        break

            async with self._lock:
                if self._process is not process:
                    raise CaptureError("Dialog recording was aborted.")

                active_process, active_path = self._take_active_recording()
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

            self._write_pcm_wav(
                active_path,
                pcm,
                self._dialog_sample_rate_hz,
            )
            streaming = self._streaming
            if streaming is None:
                raise CaptureError("Dialog PCM stream was lost.")
            chunk_directory = streaming.chunk_directory
            await self._finish_pcm_stream()
            return self._with_chunk_directory(
                active_path,
                chunk_directory,
            )
        except BaseException:
            if process_owned:
                await self._discard_if_active(process, path)
            else:
                path.unlink(missing_ok=True)
            self._discard_pcm_stream()
            raise

    async def abort(self) -> None:
        """Stop and discard the active recording and all streamed chunks."""
        async with self._lock:
            if self._process is None or self._path is None:
                return
            process, path = self._take_active_recording()
            pcm_task, self._pcm_task = self._pcm_task, None

        if pcm_task is not None:
            pcm_task.cancel()
            await asyncio.gather(pcm_task, return_exceptions=True)

        await self._finish_process(process)
        path.unlink(missing_ok=True)
        self._discard_pcm_stream()

    async def _pump_pcm(
        self,
        stdout: asyncio.StreamReader,
    ) -> None:
        bytes_per_chunk = max(2, self._dialog_sample_rate_hz // 5 * 2)
        pending = b""

        while True:
            pcm = await stdout.read(bytes_per_chunk)
            if not pcm:
                if pending:
                    raise CaptureError(
                        "pw-record produced an incomplete PCM sample.",
                    )
                return

            pcm = pending + pcm
            if len(pcm) % 2:
                pending, pcm = pcm[-1:], pcm[:-1]
            else:
                pending = b""
            if pcm:
                await self._add_pcm(pcm)

    @staticmethod
    def _write_pcm_wav(
        path: Path,
        pcm: bytes | bytearray,
        sample_rate_hz: int,
    ) -> None:
        with wave.open(str(path), "wb") as recording:
            recording.setnchannels(1)
            recording.setsampwidth(2)
            recording.setframerate(sample_rate_hz)
            recording.writeframes(pcm)

    @staticmethod
    def _with_chunk_directory(
        path: Path,
        chunk_directory: Path,
    ) -> CapturedAudio:
        captured = inspect_wav(path)
        return CapturedAudio(
            path=captured.path,
            duration_seconds=captured.duration_seconds,
            sample_rate_hz=captured.sample_rate_hz,
            channels=captured.channels,
            chunk_directory=chunk_directory,
        )

    async def _add_pcm(self, pcm: bytes) -> None:
        """Append PCM and publish newly complete Whisper windows."""
        streaming = self._streaming
        if streaming is None:
            raise CaptureError("PCM streaming is not active.")
        if len(pcm) % 2:
            raise CaptureError("pw-record produced an incomplete PCM sample.")

        streaming.pcm.extend(pcm)
        if streaming.chunk_sink is None:
            return

        for chunk in streaming.chunker.add_pcm(pcm):
            streaming.chunk_paths.append(chunk.path)
            await streaming.chunk_sink(chunk)

    async def _finish_pcm_stream(self) -> None:
        """Publish the single final Whisper tail after capture has ended."""
        streaming, self._streaming = self._streaming, None
        if streaming is None or streaming.chunk_sink is None:
            return

        for chunk in streaming.chunker.finish():
            streaming.chunk_paths.append(chunk.path)
            await streaming.chunk_sink(chunk)

    def _start_pcm_stream(
        self,
        *,
        path: Path,
        sample_rate_hz: int,
        chunk_sink: ChunkSink | None,
    ) -> None:
        chunk_directory = Path(
            tempfile.mkdtemp(
                prefix=f"{path.stem}-whisper-",
                dir=path.parent,
            )
        )
        self._streaming = _StreamingCapture(
            pcm=bytearray(),
            chunker=StreamingPcmChunker(
                sample_rate_hz=sample_rate_hz,
                output_directory=chunk_directory,
            ),
            chunk_sink=chunk_sink,
            chunk_paths=[],
            chunk_directory=chunk_directory,
        )

    def _discard_pcm_stream(self) -> None:
        streaming, self._streaming = self._streaming, None
        if streaming is None:
            return
        for path in streaming.chunk_paths:
            path.unlink(missing_ok=True)
        streaming.chunk_directory.rmdir()

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

        await self._finish_process(active_process)
        active_path.unlink(missing_ok=True)

    @staticmethod
    async def _finish_process(
        process: CaptureProcess,
        *,
        send_sigint: bool = True,
    ) -> tuple[bytes | None, bytes | None]:
        if send_sigint and process.returncode is None:
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
