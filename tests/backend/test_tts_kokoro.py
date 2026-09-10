"""Unit tests for the Kikiri/Kokoro TTS adapter."""

from pathlib import Path
from typing import Any

import pytest

from app.tts.kokoro import KokoroTextToSpeech


class FakePipeline:
    def __call__(
        self,
        text: str,
        *,
        voice: Any,
        speed: int,
    ):
        assert text == "Hallo Flo"
        assert voice == "victoria"
        assert speed == 1

        yield None, None, [0.1, -0.1, 0.05]


class CapturingPipeline:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def __call__(
        self,
        text: str,
        *,
        voice: Any,
        speed: int,
    ):
        self.texts.append(text)
        assert voice == "victoria"
        assert speed == 1

        yield None, None, [0.1, -0.1, 0.05]


@pytest.mark.asyncio
async def test_kokoro_loads_lazily_and_returns_wav(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = KokoroTextToSpeech(
        device="cpu",
        model_path=Path("unused-model.pth"),
        voice_path=Path("unused-voice.pt"),
        config_path=Path("unused-config.json"),
    )
    load_count = 0

    def fake_load_runtime():
        nonlocal load_count
        load_count += 1
        return object(), FakePipeline(), "victoria", "cpu"

    monkeypatch.setattr(
        engine,
        "_load_runtime",
        fake_load_runtime,
    )

    assert load_count == 0

    first = await engine.synthesize("Hallo Flo")
    second = await engine.synthesize("Hallo Flo")

    assert first.startswith(b"RIFF")
    assert second.startswith(b"RIFF")
    assert load_count == 1


@pytest.mark.asyncio
async def test_kokoro_removes_emojis_before_synthesis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = KokoroTextToSpeech(
        device="cpu",
        model_path=Path("unused-model.pth"),
        voice_path=Path("unused-voice.pt"),
        config_path=Path("unused-config.json"),
    )
    pipeline = CapturingPipeline()

    monkeypatch.setattr(
        engine,
        "_load_runtime",
        lambda: (object(), pipeline, "victoria", "cpu"),
    )

    audio = await engine.synthesize(
        "Hallo👋🏽 Flo#️⃣🇩🇪👩‍💻!"
    )

    assert audio.startswith(b"RIFF")
    assert pipeline.texts == ["Hallo Flo!"]


@pytest.mark.asyncio
async def test_kokoro_rejects_emoji_only_text() -> None:
    engine = KokoroTextToSpeech()

    with pytest.raises(
        ValueError,
        match="TTS text must not be empty",
    ):
        await engine.synthesize("👋🏽")


@pytest.mark.asyncio
async def test_kokoro_unload_releases_lazy_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = KokoroTextToSpeech(
        device="cpu",
        model_path=Path("unused-model.pth"),
        voice_path=Path("unused-voice.pt"),
        config_path=Path("unused-config.json"),
    )
    load_count = 0

    def fake_load_runtime():
        nonlocal load_count
        load_count += 1
        return object(), FakePipeline(), "victoria", "cpu"

    monkeypatch.setattr(
        engine,
        "_load_runtime",
        fake_load_runtime,
    )

    await engine.synthesize("Hallo Flo")
    await engine.unload()
    await engine.synthesize("Hallo Flo")

    assert load_count == 2


@pytest.mark.asyncio
async def test_kokoro_rejects_empty_text() -> None:
    engine = KokoroTextToSpeech()

    with pytest.raises(
        ValueError,
        match="TTS text must not be empty",
    ):
        await engine.synthesize("   ")


@pytest.mark.asyncio
async def test_kokoro_reports_missing_local_artifact(
    tmp_path: Path,
) -> None:
    engine = KokoroTextToSpeech(
        device="cpu",
        model_path=tmp_path / "missing-model.pth",
        voice_path=tmp_path / "missing-voice.pt",
        config_path=tmp_path / "missing-config.json",
    )

    with pytest.raises(
        RuntimeError,
        match="Kokoro model artifact is missing:",
    ):
        await engine.synthesize("Hallo Flo")
