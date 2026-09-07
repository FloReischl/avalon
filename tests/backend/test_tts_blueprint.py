import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.tts.chatterbox import ChatterboxTextToSpeech


class FakeTensor:
    def cpu(self):
        return self


class FakeModel:
    sr = 24_000

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def generate(
        self,
        text: str,
        *,
        language_id: str,
        audio_prompt_path: str,
    ) -> FakeTensor:
        self.calls.append((text, language_id, audio_prompt_path))
        return FakeTensor()


@pytest.mark.asyncio
async def test_chatterbox_tts_loads_lazily_and_returns_wav_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference = tmp_path / "reference.wav"
    reference.write_bytes(b"reference")

    model = FakeModel()
    loads = 0

    tts = ChatterboxTextToSpeech(
        device="cpu",
        reference_audio=reference,
    )

    def load_model():
        nonlocal loads
        loads += 1
        return model, "cpu"

    def save(output, wav, sample_rate, *, format):
        assert isinstance(wav, FakeTensor)
        assert sample_rate == 24_000
        assert format == "wav"
        output.write(b"RIFFfake-WAVE")

    monkeypatch.setattr(tts, "_load_model", load_model)
    monkeypatch.setitem(
        sys.modules,
        "torchaudio",
        SimpleNamespace(save=save),
    )

    first = await tts.synthesize("Hallo Flo")
    second = await tts.synthesize("Noch einmal")

    assert first == b"RIFFfake-WAVE"
    assert second == b"RIFFfake-WAVE"
    assert loads == 1
    assert model.calls == [
        ("Hallo Flo", "de", str(reference)),
        ("Noch einmal", "de", str(reference)),
    ]


@pytest.mark.asyncio
async def test_chatterbox_tts_unload_forces_lazy_reload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference = tmp_path / "reference.wav"
    reference.write_bytes(b"reference")

    loads = 0
    tts = ChatterboxTextToSpeech(
        device="cpu",
        reference_audio=reference,
    )

    def load_model():
        nonlocal loads
        loads += 1
        return FakeModel(), "cpu"

    def save(output, wav, sample_rate, *, format):
        output.write(b"RIFFfake-WAVE")

    monkeypatch.setattr(tts, "_load_model", load_model)
    monkeypatch.setitem(
        sys.modules,
        "torchaudio",
        SimpleNamespace(save=save),
    )

    await tts.synthesize("Hallo")
    await tts.unload()
    await tts.synthesize("Hallo wieder")

    assert loads == 2


@pytest.mark.asyncio
async def test_chatterbox_tts_rejects_missing_reference_audio(
    tmp_path: Path,
) -> None:
    tts = ChatterboxTextToSpeech(
        device="cpu",
        reference_audio=tmp_path / "missing.wav",
    )

    with pytest.raises(RuntimeError, match="reference audio is missing"):
        await tts.synthesize("Hallo")


@pytest.mark.asyncio
async def test_chatterbox_tts_rejects_empty_text(tmp_path: Path) -> None:
    reference = tmp_path / "reference.wav"
    reference.write_bytes(b"reference")
    tts = ChatterboxTextToSpeech(
        device="cpu",
        reference_audio=reference,
    )

    with pytest.raises(ValueError, match="must not be empty"):
        await tts.synthesize("   ")

