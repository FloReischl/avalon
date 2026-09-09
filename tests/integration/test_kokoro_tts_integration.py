"""Integration test for the productive Kikiri/Kokoro Victoria TTS setup."""

from __future__ import annotations

import os
import wave
from io import BytesIO
from pathlib import Path

import pytest
import torch

from app.config import settings
from app.tts.kokoro import KokoroTextToSpeech


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _integration_enabled() -> bool:
    return os.getenv("AVALO_RUN_TTS_INTEGRATION") == "1"


def _assert_valid_wav(audio: bytes) -> None:
    assert audio.startswith(b"RIFF")
    assert len(audio) > 44

    with wave.open(BytesIO(audio), "rb") as wav:
        assert wav.getnchannels() >= 1
        assert wav.getframerate() == 24000
        assert wav.getnframes() > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kokoro_victoria_real_synthesis_load_unload_reload() -> None:
    if not _integration_enabled():
        pytest.skip("Set AVALO_RUN_TTS_INTEGRATION=1 to run real TTS integration.")

    expected_artifacts = [
        PROJECT_ROOT / settings.tts_kokoro_config,
        PROJECT_ROOT / settings.tts_kokoro_model,
        PROJECT_ROOT / settings.tts_kokoro_voice,
    ]

    missing = [
        str(path)
        for path in expected_artifacts
        if not path.is_file()
    ]
    assert not missing, (
        "Required Kokoro Victoria artifacts are missing: "
        + ", ".join(missing)
    )

    engine = KokoroTextToSpeech(device="auto")

    first_audio = await engine.synthesize(
        "Hallo Flo. Dies ist ein Integrationstest für Avalo."
    )

    _assert_valid_wav(first_audio)

    expected_device = "cuda" if torch.cuda.is_available() else "cpu"
    assert engine._device == expected_device
    assert engine._model is not None
    assert engine._pipeline is not None
    assert engine._voice is not None

    await engine.unload()

    assert engine._device is None
    assert engine._model is None
    assert engine._pipeline is None
    assert engine._voice is None

    second_audio = await engine.synthesize(
        "Der Kokoro Sprachgenerator wurde erfolgreich erneut geladen."
    )

    _assert_valid_wav(second_audio)
    assert engine._device == expected_device

    await engine.unload()


_KOKORO_ASSETS = [
    (
        "Hallo Flo.",
        "data/tts/generated/greeting.wav",
    ),
    (
        "Der Agent ist fertig.",
        "data/tts/generated/agent-finished.wav",
    ),
]


@pytest.mark.integration
@pytest.mark.skip(reason="Manual Kokoro static WAV asset generation.")
@pytest.mark.parametrize(("text", "file"), _KOKORO_ASSETS)
@pytest.mark.asyncio
async def test_generate_static_kokoro_wav_asset(
    text: str,
    file: str,
) -> None:
    """Generate reusable static WAV assets using Kokoro Victoria."""
    config_path = PROJECT_ROOT / "data/tts/kokoro_victoria/config.json"
    model_path = (
        PROJECT_ROOT
        / "data/tts/kokoro_victoria/kikiri_german_victoria_ep10.pth"
    )
    voice_path = PROJECT_ROOT / "data/tts/kokoro_victoria/victoria.pt"

    engine = KokoroTextToSpeech(
        device="auto",
        config_path=config_path,
        model_path=model_path,
        voice_path=voice_path,
    )

    try:
        audio = await engine.synthesize(text)
        _assert_valid_wav(audio)

        output_path = PROJECT_ROOT / file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio)
    finally:
        await engine.unload()
