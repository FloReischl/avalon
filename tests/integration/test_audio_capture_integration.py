"""Opt-in hardware integration test for local microphone capture."""

import asyncio
import os

import pytest

from app.audio.capture import PipeWireRecorder


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(
    os.environ.get("AVALO_TEST_MICROPHONE") != "1",
    reason="requires explicit microphone test opt-in",
)
async def test_pipewire_records_nonempty_wav() -> None:
    recorder = PipeWireRecorder()

    await recorder.start()
    await asyncio.sleep(5)
    capture = await recorder.stop()

    try:
        assert capture.path.stat().st_size > 44
        assert capture.duration_seconds > 0
    finally:
        capture.path.unlink(missing_ok=True)
