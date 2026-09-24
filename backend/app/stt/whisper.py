"""CPU-only faster-whisper speech-to-text service."""
from __future__ import annotations

import asyncio
import gc
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

WINDOW_SECONDS = 10.0
OVERLAP_SECONDS = 2.0
STEP_SECONDS = WINDOW_SECONDS - OVERLAP_SECONDS
IDLE_UNLOAD_SECONDS = 600.0

@dataclass(frozen=True, slots=True)
class AudioChunk:
    path: Path
    start_seconds: float
    end_seconds: float

def create_audio_chunks(path: Path, output_directory: Path) -> list[AudioChunk]:
    """Create spike-compatible 10 s WAV windows with 2 s overlap."""
    chunks: list[AudioChunk] = []
    with wave.open(str(path), "rb") as source:
        rate, total = source.getframerate(), source.getnframes()
        if rate <= 0 or total <= 0:
            raise ValueError("Audio must contain at least one frame.")
        window, step, start, index = int(WINDOW_SECONDS * rate), int(STEP_SECONDS * rate), 0, 0
        while start < total:
            end = min(start + window, total)
            source.setpos(start)
            chunk_path = output_directory / f"whisper-chunk-{index:03d}.wav"
            with wave.open(str(chunk_path), "wb") as target:
                target.setparams(source.getparams())
                target.writeframes(source.readframes(end - start))
            chunks.append(AudioChunk(chunk_path, start / rate, end / rate))
            if end == total:
                break
            start, index = start + step, index + 1
    return chunks

def merge_transcripts(previous: str, current: str) -> str:
    """Merge with the spike's longest exact normalized word overlap."""
    if not previous:
        return current.strip()
    old, new = previous.split(), current.split()
    def normalize(word: str) -> str:
        return word.lower().strip(".,!?;:\"'()")
    overlap = 0
    old_normalized, new_normalized = list(map(normalize, old)), list(map(normalize, new))
    for size in range(1, min(len(old), len(new)) + 1):
        if old_normalized[-size:] == new_normalized[:size]:
            overlap = size
    appended = new[overlap:]
    return previous.strip() if not appended else f"{previous.rstrip()} {' '.join(appended)}"

class FasterWhisperSttService:
    """Lazy CPU/int8 Whisper lifecycle with serialized inference."""
    def __init__(self, *, idle_unload_seconds: float = IDLE_UNLOAD_SECONDS, model_factory: Callable[..., Any] | None = None) -> None:
        self._idle_unload_seconds = idle_unload_seconds
        self._model_factory = model_factory
        self._model: Any | None = None
        self._lock = asyncio.Lock()
        self._audio_call_active = False
        self._idle_task: asyncio.Task[None] | None = None

    async def warm_up(self) -> None:
        async with self._lock:
            self._cancel_idle()
            await asyncio.to_thread(self._ensure_model)
            self._schedule_idle()

    async def transcribe(self, audio_path: Path) -> str:
        """Run one chunk, never concurrently with another Whisper inference."""
        work = asyncio.create_task(
            self._transcribe_locked(audio_path),
            name="avalon-whisper-inference",
        )
        try:
            return await asyncio.shield(work)
        except asyncio.CancelledError:
            # asyncio cannot stop the worker thread. Let it finish while it
            # continues to own the single-flight lock, but do not make the
            # cancelled audio turn wait for it.
            work.add_done_callback(self._consume_background_result)
            raise

    async def _transcribe_locked(self, audio_path: Path) -> str:
        async with self._lock:
            self._cancel_idle()
            try:
                return await asyncio.to_thread(
                    self._transcribe_sync,
                    audio_path,
                )
            finally:
                self._schedule_idle()

    @staticmethod
    def _consume_background_result(task: asyncio.Task[str]) -> None:
        try:
            task.result()
        except BaseException:
            pass

    async def set_audio_call_active(self, active: bool) -> None:
        async with self._lock:
            self._audio_call_active = active
            if active:
                self._cancel_idle()
            else:
                self._schedule_idle()

    async def unload(self) -> None:
        async with self._lock:
            self._cancel_idle()
            await asyncio.to_thread(self._unload_sync)

    def _ensure_model(self) -> Any:
        if self._model is None:
            factory = self._model_factory
            if factory is None:
                from faster_whisper import WhisperModel
                factory = WhisperModel
            self._model = factory("small", device="cpu", compute_type="int8")
        return self._model

    def _transcribe_sync(self, path: Path) -> str:
        segments, _info = self._ensure_model().transcribe(str(path), language="de", beam_size=5)
        return "".join(segment.text for segment in segments).strip()

    def _unload_sync(self) -> None:
        self._model = None
        gc.collect()

    def _cancel_idle(self) -> None:
        task, self._idle_task = self._idle_task, None
        if task is not None:
            task.cancel()

    def _schedule_idle(self) -> None:
        if self._audio_call_active or self._model is None:
            return
        self._cancel_idle()
        self._idle_task = asyncio.create_task(self._unload_after_idle())

    async def _unload_after_idle(self) -> None:
        current = asyncio.current_task()
        try:
            await asyncio.sleep(self._idle_unload_seconds)
            async with self._lock:
                if not self._audio_call_active:
                    await asyncio.to_thread(self._unload_sync)
        except asyncio.CancelledError:
            return
        finally:
            if self._idle_task is current:
                self._idle_task = None


class StreamingPcmChunker:
    """Create deterministic overlapping Whisper WAV windows from PCM input."""

    def __init__(
        self,
        *,
        sample_rate_hz: int,
        output_directory: Path,
    ) -> None:
        self._sample_rate_hz = sample_rate_hz
        self._output_directory = output_directory
        self._window_frames = int(WINDOW_SECONDS * sample_rate_hz)
        self._step_frames = int(STEP_SECONDS * sample_rate_hz)
        self._pcm = bytearray()
        self._next_start_frame = 0
        self._covered_through_frame = 0
        self._index = 0

    def add_pcm(self, pcm: bytes) -> list[AudioChunk]:
        """Return every complete 10-second window newly available."""
        if len(pcm) % 2:
            raise ValueError("PCM must contain complete 16-bit samples.")
        self._pcm.extend(pcm)
        return self._complete_chunks()

    def finish(self) -> list[AudioChunk]:
        """Return one final tail only for audio not covered by a full window."""
        total_frames = len(self._pcm) // 2
        if total_frames <= self._covered_through_frame:
            return []
        if self._next_start_frame >= total_frames:
            return []

        chunk = self._write_chunk(self._next_start_frame, total_frames)
        self._next_start_frame = total_frames
        self._covered_through_frame = total_frames
        return [chunk]

    def _complete_chunks(self) -> list[AudioChunk]:
        total_frames = len(self._pcm) // 2
        chunks: list[AudioChunk] = []
        while self._next_start_frame + self._window_frames <= total_frames:
            end_frame = self._next_start_frame + self._window_frames
            chunks.append(
                self._write_chunk(
                    self._next_start_frame,
                    end_frame,
                )
            )
            self._covered_through_frame = end_frame
            self._next_start_frame += self._step_frames
        return chunks

    def _write_chunk(self, start_frame: int, end_frame: int) -> AudioChunk:
        path = self._output_directory / f"whisper-chunk-{self._index:03d}.wav"
        self._index += 1
        with wave.open(str(path), "wb") as target:
            target.setnchannels(1)
            target.setsampwidth(2)
            target.setframerate(self._sample_rate_hz)
            target.writeframes(self._pcm[start_frame * 2 : end_frame * 2])
        return AudioChunk(
            path=path,
            start_seconds=start_frame / self._sample_rate_hz,
            end_seconds=end_frame / self._sample_rate_hz,
        )
