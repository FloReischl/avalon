"""Sequential faster-whisper to text-LLM audio orchestration."""

import asyncio
import shutil
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.audio.capture import CapturedAudio, PipeWireRecorder
from app.persistence.chat_repository import ChatRepository
from app.runtime.base import ModelRuntime
from app.services.context_compression import (
    ContextCompressionService,
    build_active_context,
    parse_compressed_context,
)
from app.stt.whisper import (
    AudioChunk,
    FasterWhisperSttService,
    merge_transcripts,
)
from app.user_config import AvatarConfig

STT_COMPLETION_TIMEOUT_SECONDS = 30.0


class AudioTurnError(RuntimeError):
    """A client-visible audio turn failure."""


@dataclass(frozen=True, slots=True)
class AudioStreamEvent:
    kind: Literal["chat", "assistant", "transcript", "assistant_done", "processing"]
    text: str = ""


@dataclass(slots=True)
class _StreamingTranscription:
    """One capture-local, serial Whisper work queue."""

    stt: FasterWhisperSttService
    queue: asyncio.Queue[AudioChunk | None]
    transcript: str = ""
    task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self.task = asyncio.create_task(
            self._consume(),
            name="avalo-streaming-whisper",
        )

    async def enqueue(self, chunk: AudioChunk) -> None:
        self.queue.put_nowait(chunk)

    async def finish(self) -> str:
        self.queue.put_nowait(None)
        if self.task is None:
            raise RuntimeError("Streaming transcription was not started.")
        try:
            await asyncio.wait_for(
                asyncio.shield(self.task),
                timeout=STT_COMPLETION_TIMEOUT_SECONDS,
            )
        except TimeoutError as exc:
            raise AudioTurnError("Sprachverarbeitung abgelaufen") from exc
        return self.transcript.strip()

    async def cancel(self) -> None:
        if self.task is None:
            return
        self.task.cancel()
        await asyncio.gather(self.task, return_exceptions=True)

    async def _consume(self) -> None:
        while True:
            chunk = await self.queue.get()
            if chunk is None:
                return
            try:
                self.transcript = merge_transcripts(
                    self.transcript,
                    await self.stt.transcribe(chunk.path),
                )
            except Exception as exc:
                raise AudioTurnError(
                    "Sprachverarbeitung fehlgeschlagen",
                ) from exc


class AudioTextChatService:
    """Turn captured speech into a final text turn before LLM generation."""

    def __init__(
        self,
        recorder: PipeWireRecorder,
        runtime: ModelRuntime,
        repository: ChatRepository | None = None,
        avatar_provider: Callable[[], AvatarConfig] | None = None,
        compression_service: ContextCompressionService | None = None,
        stt: FasterWhisperSttService | None = None,
    ) -> None:
        self._recorder = recorder
        self._runtime = runtime
        self._repository = repository
        self._avatar_provider = avatar_provider
        self._compression_service = compression_service
        self._stt = stt or FasterWhisperSttService()
        self._compression_tasks: set[asyncio.Task[object]] = set()
        self._recording_transcription: _StreamingTranscription | None = None
        self._recording_warmup_task: asyncio.Task[None] | None = None

    async def start_recording(self) -> None:
        if self._recording_transcription is not None:
            raise AudioTurnError("Eine Sprachaufnahme läuft bereits.")

        transcription = _StreamingTranscription(
            stt=self._stt,
            queue=asyncio.Queue(),
        )
        transcription.start()
        self._recording_transcription = transcription
        try:
            # Capture must become active immediately. Whisper loading starts
            # independently afterwards and must not delay microphone startup.
            await self._recorder.start(transcription.enqueue)
            warmup_task = asyncio.create_task(
                self._warm_up_ptt(transcription),
                name="avalo-ptt-whisper-warmup",
            )
            warmup_task.add_done_callback(self._consume_background_task_result)
            self._recording_warmup_task = warmup_task
        except BaseException:
            self._recording_transcription = None
            await transcription.cancel()
            raise

    async def _warm_up_ptt(
        self,
        transcription: _StreamingTranscription,
    ) -> None:
        try:
            await self._stt.warm_up()
        except BaseException as exc:
            if self._recording_transcription is transcription:
                await self._recorder.abort()
            raise AudioTurnError(
                "Sprachverarbeitung konnte nicht gestartet werden",
            ) from exc

    @staticmethod
    def _consume_background_task_result(task: asyncio.Task[None]) -> None:
        try:
            task.result()
        except BaseException:
            pass

    async def abort_recording(self) -> None:
        transcription, self._recording_transcription = (
            self._recording_transcription,
            None,
        )
        self._recording_warmup_task = None
        try:
            await self._recorder.abort()
        finally:
            if transcription is not None:
                await transcription.cancel()

    async def warm_up_stt(self) -> None:
        """Load Whisper before an audio call becomes active."""
        await self._stt.warm_up()

    async def set_audio_call_active(self, active: bool) -> None:
        """Keep Whisper resident for the duration of an active audio call."""
        await self._stt.set_audio_call_active(active)

    def terminal_compression_error(
        self,
        chat_id: int | None,
    ) -> str | None:
        if chat_id is None or self._repository is None:
            return None
        chat = self._repository.get_chat(chat_id)
        return None if chat is None else chat.compression_error_code

    async def stream_response_with_transcription(
        self,
        messages: list[dict[str, str]],
        chat_id: int | None = None,
    ) -> AsyncIterator[AudioStreamEvent]:
        transcription, self._recording_transcription = (
            self._recording_transcription,
            None,
        )
        warmup_task, self._recording_warmup_task = (
            self._recording_warmup_task,
            None,
        )
        if transcription is None:
            raise AudioTurnError("Keine aktive Sprachaufnahme.")

        captured: CapturedAudio | None = None
        try:
            # A warm-up failure may already have aborted capture. Surface that
            # failure before asking the recorder to stop a no-longer-active
            # recording.
            if warmup_task is not None and warmup_task.done():
                await warmup_task

            captured = await self._recorder.stop()

            # Recording stops immediately when requested; only afterwards may
            # we wait for a still-running model load.
            if warmup_task is not None:
                await warmup_task

            transcript = await transcription.finish()
        except BaseException:
            if captured is not None:
                await self._cleanup_capture(captured)
            await transcription.cancel()
            raise

        async for event in self._stream_turn(
            captured,
            messages,
            chat_id,
            transcript=transcript,
        ):
            yield event

    async def stream_dialog_response_with_transcription(
        self,
        messages: list[dict[str, str]],
        chat_id: int | None = None,
    ) -> AsyncIterator[AudioStreamEvent]:
        transcription = _StreamingTranscription(
            stt=self._stt,
            queue=asyncio.Queue(),
        )
        transcription.start()

        captured: CapturedAudio | None = None
        try:
            captured = await self._recorder.capture_dialog_turn(
                transcription.enqueue,
            )
            yield AudioStreamEvent(kind="processing")
            transcript = await transcription.finish()
        except BaseException:
            if captured is not None:
                await self._cleanup_capture(captured)
            await transcription.cancel()
            raise

        async for event in self._stream_turn(
            captured,
            messages,
            chat_id,
            transcript=transcript,
        ):
            yield event

    async def _stream_turn(
        self,
        captured: CapturedAudio,
        messages: list[dict[str, str]],
        chat_id: int | None,
        *,
        transcript: str,
    ) -> AsyncIterator[AudioStreamEvent]:
        try:
            if not transcript.strip():
                raise AudioTurnError("Keine Sprache erkannt")

            context, persistent_chat_id = self._persist_and_build_context(
                transcript,
                messages,
                chat_id,
            )
            yield AudioStreamEvent(kind="transcript", text=transcript)
            if persistent_chat_id is not None:
                yield AudioStreamEvent(kind="chat", text=str(persistent_chat_id))

            assistant_chunks: list[str] = []
            async for chunk in self._runtime.generate_text_stream(context):
                assistant_chunks.append(chunk)
                yield AudioStreamEvent(kind="assistant", text=chunk)

            if not assistant_chunks:
                raise AudioTurnError("Sprachantwort konnte nicht erzeugt werden")

            if persistent_chat_id is not None:
                self._repository.add_message(
                    persistent_chat_id,
                    "assistant",
                    "".join(assistant_chunks),
                )
                self._schedule_compression(persistent_chat_id)
            yield AudioStreamEvent(kind="assistant_done")
        except TimeoutError as exc:
            raise AudioTurnError("Sprachverarbeitung abgelaufen") from exc
        finally:
            await self._cleanup_capture(captured)

    @staticmethod
    async def _cleanup_capture(captured: CapturedAudio) -> None:
        captured.path.unlink(missing_ok=True)
        if captured.chunk_directory is not None:
            await asyncio.to_thread(
                shutil.rmtree,
                captured.chunk_directory,
                ignore_errors=True,
            )

    def _persist_and_build_context(
        self,
        transcript: str,
        messages: list[dict[str, str]],
        chat_id: int | None,
    ) -> tuple[list[dict[str, str]], int | None]:
        if self._repository is None:
            return [*messages, {"role": "user", "content": transcript}], None

        if chat_id is None:
            chat = self._repository.create_chat_with_message(
                datetime.now().strftime("New %Y-%m-%d %H:%M:%S"),
                "user",
                transcript,
            )
            context = list(messages)
            if self._avatar_provider is not None:
                avatar = self._avatar_provider()
                context.insert(0, {"role": "system", "content": f"{avatar.persona}\n\n{avatar.instructions}"})
            return [*context, {"role": "user", "content": transcript}], chat.id

        chat = self._repository.get_chat(chat_id)
        if chat is None:
            raise ValueError(f"Chat {chat_id} does not exist.")
        if chat.compression_error_code is not None:
            raise ValueError(chat.compression_error_code)
        self._repository.add_message(chat_id, "user", transcript)
        context = build_active_context(
            self._repository.get_messages(chat_id),
            parse_compressed_context(chat.compressed_context),
            chat.compressed_through_seq,
            self._avatar_provider() if self._avatar_provider else None,
        )
        return context, chat_id

    def _schedule_compression(self, chat_id: int) -> None:
        if self._repository is None:
            return
        service = self._compression_service or ContextCompressionService(
            self._runtime,
            self._repository,
            self._avatar_provider() if self._avatar_provider else None,
        )
        task = asyncio.create_task(service.compress_if_needed(chat_id))
        self._compression_tasks.add(task)
        task.add_done_callback(self._compression_tasks.discard)
