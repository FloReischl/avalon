"""Push-to-talk audio chat orchestration."""

from collections.abc import AsyncIterator

from app.audio.capture import CapturedAudio, PipeWireRecorder
from app.runtime.base import ModelRuntime


class AudioChatService:
    """Own one backend recorder and turn completed audio into chat output."""

    def __init__(self, recorder: PipeWireRecorder, runtime: ModelRuntime) -> None:
        self._recorder = recorder
        self._runtime = runtime

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
