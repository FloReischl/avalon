"""Tests for TTS synthesis and playback lifecycle."""

import asyncio

import pytest

from app.services.tts import TtsBusyError, TtsService


class FakeTextToSpeech:
    def __init__(self) -> None:
        self.synthesized: list[str] = []
        self.unload_count = 0

    async def synthesize(self, text: str) -> bytes:
        self.synthesized.append(text)
        return b"RIFFfake-WAVE"

    async def unload(self) -> None:
        self.unload_count += 1


@pytest.mark.asyncio
async def test_synthesize_returns_audio_and_unique_playback_ids() -> None:
    engine = FakeTextToSpeech()
    service = TtsService(engine)

    first = await service.synthesize("Hallo")
    second = await service.synthesize("Nochmal")

    assert first.audio == b"RIFFfake-WAVE"
    assert second.audio == b"RIFFfake-WAVE"
    assert first.playback_id != second.playback_id
    assert engine.synthesized == ["Hallo", "Nochmal"]


@pytest.mark.asyncio
async def test_playback_end_unloads_after_idle_timeout() -> None:
    engine = FakeTextToSpeech()
    service = TtsService(
        engine,
        idle_unload_seconds=0.01,
    )

    result = await service.synthesize("Hallo")
    await service.playback_ended(result.playback_id)

    assert engine.unload_count == 0

    await asyncio.sleep(0.03)

    assert engine.unload_count == 1


@pytest.mark.asyncio
async def test_stale_playback_end_does_not_start_unload_timer() -> None:
    engine = FakeTextToSpeech()
    service = TtsService(
        engine,
        idle_unload_seconds=0.01,
    )

    first = await service.synthesize("Erste Nachricht")
    second = await service.synthesize("Zweite Nachricht")

    await service.playback_ended(first.playback_id)
    await asyncio.sleep(0.03)

    assert engine.unload_count == 0

    await service.playback_ended(second.playback_id)
    await asyncio.sleep(0.03)

    assert engine.unload_count == 1


@pytest.mark.asyncio
async def test_new_synthesis_cancels_pending_idle_unload() -> None:
    engine = FakeTextToSpeech()
    service = TtsService(
        engine,
        idle_unload_seconds=0.03,
    )

    first = await service.synthesize("Erste Nachricht")
    await service.playback_ended(first.playback_id)

    await asyncio.sleep(0.01)
    second = await service.synthesize("Zweite Nachricht")

    await asyncio.sleep(0.04)

    assert engine.unload_count == 0

    await service.playback_ended(second.playback_id)
    await asyncio.sleep(0.04)

    assert engine.unload_count == 1


@pytest.mark.asyncio
async def test_concurrent_synthesis_is_rejected_instead_of_queued() -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    class BlockingTextToSpeech(FakeTextToSpeech):
        async def synthesize(self, text: str) -> bytes:
            self.synthesized.append(text)
            started.set()
            await release.wait()
            return b"RIFFfake-WAVE"

    engine = BlockingTextToSpeech()
    service = TtsService(engine)

    first_task = asyncio.create_task(service.synthesize("Erste Nachricht"))
    await started.wait()

    with pytest.raises(TtsBusyError, match="already active"):
        await service.synthesize("Zweite Nachricht")

    release.set()
    first = await first_task

    assert first.audio == b"RIFFfake-WAVE"
    assert engine.synthesized == ["Erste Nachricht"]


@pytest.mark.asyncio
async def test_cancelled_request_keeps_synthesis_busy_until_engine_finishes() -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    class BlockingTextToSpeech(FakeTextToSpeech):
        async def synthesize(self, text: str) -> bytes:
            self.synthesized.append(text)
            started.set()
            await release.wait()
            return b"RIFFfake-WAVE"

    engine = BlockingTextToSpeech()
    service = TtsService(engine)

    cancelled_request = asyncio.create_task(
        service.synthesize("Erste Nachricht")
    )
    await started.wait()

    cancelled_request.cancel()
    await asyncio.sleep(0)

    with pytest.raises(TtsBusyError, match="already active"):
        await service.synthesize("Zweite Nachricht")

    release.set()

    with pytest.raises(asyncio.CancelledError):
        await cancelled_request

    result = await service.synthesize("Dritte Nachricht")

    assert result.audio == b"RIFFfake-WAVE"
    assert engine.synthesized == [
        "Erste Nachricht",
        "Dritte Nachricht",
    ]
