"""Sequential faster-whisper to text-LLM audio orchestration."""

import asyncio
import tempfile
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
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
    FasterWhisperSttService,
    create_audio_chunks,
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

    async def start_recording(self) -> None:
        await self._recorder.start()

    async def abort_recording(self) -> None:
        await self._recorder.abort()

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
        captured = await self._recorder.stop()
        async for event in self._stream_turn(captured, messages, chat_id):
            yield event

    async def stream_dialog_response_with_transcription(
        self,
        messages: list[dict[str, str]],
        chat_id: int | None = None,
    ) -> AsyncIterator[AudioStreamEvent]:
        captured = await self._recorder.capture_dialog_turn()
        yield AudioStreamEvent(kind="processing")
        async for event in self._stream_turn(captured, messages, chat_id):
            yield event

    async def _stream_turn(
        self,
        captured: CapturedAudio,
        messages: list[dict[str, str]],
        chat_id: int | None,
    ) -> AsyncIterator[AudioStreamEvent]:
        try:
            transcript = await asyncio.wait_for(
                self._transcribe(captured.path),
                timeout=STT_COMPLETION_TIMEOUT_SECONDS,
            )
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
            captured.path.unlink(missing_ok=True)

    async def _transcribe(self, path: Path) -> str:
        transcript = ""
        with tempfile.TemporaryDirectory(prefix="avalo-whisper-") as directory:
            for chunk in create_audio_chunks(path, Path(directory)):
                transcript = merge_transcripts(
                    transcript,
                    await self._stt.transcribe(chunk.path),
                )
        return transcript.strip()

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
