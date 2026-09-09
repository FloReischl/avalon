"""Push-to-talk audio chat orchestration."""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.audio.capture import CapturedAudio, PipeWireRecorder
from app.persistence.chat_repository import ChatRepository
from app.runtime.base import ModelRuntime


@dataclass(frozen=True, slots=True)
class AudioStreamEvent:
    """One independently streamed result from a captured audio turn."""

    kind: Literal[
        "chat",
        "assistant",
        "transcript",
        "assistant_done",
        "transcript_done",
        "assistant_error",
        "transcript_error",
    ]

    text: str = ""


class AudioChatService:
    """Own one backend recorder and turn completed audio into chat output."""

    def __init__(
        self,
        recorder: PipeWireRecorder,
        runtime: ModelRuntime,
        repository: ChatRepository | None = None,
    ) -> None:
        self._recorder = recorder
        self._runtime = runtime
        self._repository = repository

    async def start_recording(self) -> None:
        await self._recorder.start()

    async def abort_recording(self) -> None:
        await self._recorder.abort()

    async def stream_response(
        self,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        captured = await self._recorder.stop()
        async for chunk in self._stream_captured_response(
            captured,
            messages,
        ):
            yield chunk

    async def stream_dialog_response(
        self,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        captured = await self._recorder.capture_dialog_turn()
        async for chunk in self._stream_captured_response(
            captured,
            messages,
        ):
            yield chunk

    async def stream_response_with_transcription(
        self,
        messages: list[dict[str, str]],
        chat_id: int | None = None,
    ) -> AsyncIterator[AudioStreamEvent]:
        """Stop recording and stream response plus transcription concurrently."""
        captured = await self._recorder.stop()

        async for event in self._stream_persistent_captured_turn(
            captured,
            messages,
            chat_id,
        ):
            yield event

    async def stream_dialog_response_with_transcription(
        self,
        messages: list[dict[str, str]],
        chat_id: int | None = None,
    ) -> AsyncIterator[AudioStreamEvent]:
        """Capture a dialog turn and stream response plus transcription."""
        captured = await self._recorder.capture_dialog_turn()

        async for event in self._stream_persistent_captured_turn(
            captured,
            messages,
            chat_id,
        ):
            yield event

    async def _stream_captured_response(
        self,
        captured: CapturedAudio,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        try:
            async for chunk in self._runtime.generate_from_audio_stream(
                captured.path,
                messages,
            ):
                yield chunk
        finally:
            captured.path.unlink(missing_ok=True)

    async def _stream_persistent_captured_turn(
        self,
        captured: CapturedAudio,
        messages: list[dict[str, str]],
        chat_id: int | None,
    ) -> AsyncIterator[AudioStreamEvent]:
        persistent_chat_id: int | None = None
        user_message_id: int | None = None

        if self._repository is not None:
            if chat_id is None:
                title = datetime.now().strftime("New %Y-%m-%d %H:%M:%S")
                chat = self._repository.create_chat_with_message(
                    title,
                    "user",
                    "🎤 Sprachnachricht",
                )
                persistent_chat_id = chat.id
                user_message = self._repository.get_messages(chat.id)[0]
                user_message_id = user_message.id
            else:
                if self._repository.get_chat(chat_id) is None:
                    raise ValueError(f"Chat {chat_id} does not exist.")

                persistent_chat_id = chat_id
                user_message = self._repository.add_message(
                    chat_id,
                    "user",
                    "🎤 Sprachnachricht",
                )
                user_message_id = user_message.id

            yield AudioStreamEvent(
                kind="chat",
                text=str(persistent_chat_id),
            )

        transcript_chunks: list[str] = []
        assistant_chunks: list[str] = []

        async for event in self._stream_captured_turn(
            captured,
            messages,
        ):
            if event.kind == "transcript":
                transcript_chunks.append(event.text)
            elif event.kind == "assistant":
                assistant_chunks.append(event.text)
            elif (
                event.kind == "transcript_done"
                and self._repository is not None
                and persistent_chat_id is not None
                and user_message_id is not None
            ):
                transcript = "".join(transcript_chunks).strip()
                if transcript:
                    self._repository.update_message_content(
                        user_message_id,
                        transcript,
                    )
            elif (
                event.kind == "assistant_done"
                and self._repository is not None
                and persistent_chat_id is not None
            ):
                assistant = "".join(assistant_chunks)
                if assistant:
                    self._repository.add_message(
                        persistent_chat_id,
                        "assistant",
                        assistant,
                    )

            yield event

    async def _stream_captured_turn(
        self,
        captured: CapturedAudio,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[AudioStreamEvent]:
        queue: asyncio.Queue[
            tuple[
                Literal["assistant", "transcript"],
                str | Exception | None,
            ]
        ] = asyncio.Queue()

        async def stream_assistant() -> None:
            try:
                async for chunk in self._runtime.generate_from_audio_stream(
                    captured.path,
                    messages,
                ):
                    await queue.put(("assistant", chunk))
            except Exception as exc:
                await queue.put(("assistant", exc))
            finally:
                await queue.put(("assistant", None))

        async def stream_transcript() -> None:
            try:
                async for chunk in self._runtime.transcribe_audio_stream(
                    captured.path,
                ):
                    await queue.put(("transcript", chunk))
            except Exception as exc:
                await queue.put(("transcript", exc))
            finally:
                await queue.put(("transcript", None))

        assistant_task = asyncio.create_task(stream_assistant())
        transcript_task = asyncio.create_task(stream_transcript())
        completed = 0
        failed_sources: set[Literal["assistant", "transcript"]] = set()

        try:
            while completed < 2:
                source, value = await queue.get()

                if value is None:
                    completed += 1

                    if source not in failed_sources:
                        yield AudioStreamEvent(
                            kind=(
                                "assistant_done"
                                if source == "assistant"
                                else "transcript_done"
                            ),
                        )
                    continue

                if isinstance(value, Exception):
                    failed_sources.add(source)
                    yield AudioStreamEvent(
                        kind=(
                            "assistant_error"
                            if source == "assistant"
                            else "transcript_error"
                        ),
                    )
                    continue

                yield AudioStreamEvent(
                    kind=source,
                    text=value,
                )
        finally:
            for task in (assistant_task, transcript_task):
                if not task.done():
                    task.cancel()

            await asyncio.gather(
                assistant_task,
                transcript_task,
                return_exceptions=True,
            )
            captured.path.unlink(missing_ok=True)
