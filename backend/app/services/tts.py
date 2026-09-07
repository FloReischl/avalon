"""Application service for local text-to-speech lifecycle."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import uuid4

from app.tts.base import TextToSpeech


class TtsBusyError(RuntimeError):
    """Raised when synthesis is already in progress."""


@dataclass(frozen=True, slots=True)
class TtsResult:
    """Synthesized WAV audio and its frontend playback identity."""

    playback_id: str
    audio: bytes


class TtsService:
    """Own one local TTS engine and its synthesis/playback lifecycle."""

    def __init__(
        self,
        engine: TextToSpeech,
        *,
        idle_unload_seconds: float = 300.0,
    ) -> None:
        self._engine = engine
        self._idle_unload_seconds = idle_unload_seconds
        self._state_lock = asyncio.Lock()
        self._synthesis_active = False
        self._active_playback_id: str | None = None
        self._idle_unload_task: asyncio.Task[None] | None = None

    async def synthesize(self, text: str) -> TtsResult:
        """Synthesize one response without queueing concurrent requests."""
        async with self._state_lock:
            if self._synthesis_active:
                raise TtsBusyError("TTS synthesis is already active.")

            self._synthesis_active = True
            self._active_playback_id = None
            self._cancel_idle_unload()

        synthesis_task = asyncio.create_task(
            self._engine.synthesize(text)
        )

        try:
            audio = await asyncio.shield(synthesis_task)
        except asyncio.CancelledError:
            try:
                await asyncio.shield(synthesis_task)
            except Exception:
                pass

            async with self._state_lock:
                self._synthesis_active = False
                self._schedule_idle_unload()
            raise
        except Exception:
            async with self._state_lock:
                self._synthesis_active = False
                self._schedule_idle_unload()
            raise

        async with self._state_lock:
            self._synthesis_active = False
            playback_id = uuid4().hex
            self._active_playback_id = playback_id


        return TtsResult(
            playback_id=playback_id,
            audio=audio,
        )

    async def playback_ended(self, playback_id: str) -> None:
        """Start the idle countdown only for the currently active playback."""
        async with self._state_lock:
            if playback_id != self._active_playback_id:
                return

            self._active_playback_id = None
            self._schedule_idle_unload()

    def _cancel_idle_unload(self) -> None:
        task = self._idle_unload_task
        self._idle_unload_task = None

        if task is not None:
            task.cancel()

    def _schedule_idle_unload(self) -> None:
        self._cancel_idle_unload()
        self._idle_unload_task = asyncio.create_task(
            self._unload_after_idle()
        )

    async def _unload_after_idle(self) -> None:
        current_task = asyncio.current_task()

        try:
            await asyncio.sleep(self._idle_unload_seconds)

            async with self._state_lock:
                if (
                    self._synthesis_active
                    or self._active_playback_id is not None
                ):
                    return

                await self._engine.unload()
        except asyncio.CancelledError:
            return
        finally:
            if self._idle_unload_task is current_task:
                self._idle_unload_task = None
