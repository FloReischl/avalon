import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

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
        "torch",
        SimpleNamespace(cat=lambda chunks, dim: chunks[0]),
    )
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
        "torch",
        SimpleNamespace(cat=lambda chunks, dim: chunks[0]),
    )
    monkeypatch.setitem(
        sys.modules,
        "torchaudio",
        SimpleNamespace(save=save),
    )

    await tts.synthesize("Hallo")
    await tts.unload()
    await tts.synthesize("Hallo wieder")

    assert loads == 2


def test_chatterbox_tts_splits_at_sentence_boundaries() -> None:
    assert ChatterboxTextToSpeech._split_text(
        "Erster Satz. Zweiter Satz! Dritter Satz?"
    ) == [
        "Erster Satz.",
        "Zweiter Satz!",
        "Dritter Satz?",
    ]


def test_chatterbox_tts_splits_long_sentence_at_clause_boundary() -> None:
    first = "a" * 180 + ","
    second = "b" * 180 + "."

    assert ChatterboxTextToSpeech._split_text(
        f"{first} {second}"
    ) == [
        first,
        second,
    ]


def test_chatterbox_tts_splits_long_clause_at_whitespace() -> None:
    text = " ".join(["wort"] * 100)

    chunks = ChatterboxTextToSpeech._split_text(text)

    assert len(chunks) > 1
    assert all(len(chunk) <= 300 for chunk in chunks)
    assert " ".join(chunks) == text


def test_chatterbox_tts_loader_uses_pinned_v2_4bit_quantization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkpoint = tmp_path / "checkpoint"
    model = object()
    calls: dict[str, object] = {}

    class FakeChatterboxMultilingualTTS:
        @classmethod
        def from_local(cls, checkpoint_dir, **kwargs):
            calls["from_local"] = (Path(checkpoint_dir), kwargs)
            return model

    def snapshot_download(**kwargs):
        calls["snapshot"] = kwargs
        return str(checkpoint)

    torch_module = ModuleType("torch")
    torch_module.cuda = SimpleNamespace(is_available=lambda: True)

    chatterbox_package = ModuleType("chatterbox")
    chatterbox_package.__path__ = []
    chatterbox_module = ModuleType("chatterbox.mtl_tts")
    chatterbox_module.ChatterboxMultilingualTTS = FakeChatterboxMultilingualTTS

    huggingface_module = ModuleType("huggingface_hub")
    huggingface_module.snapshot_download = snapshot_download

    monkeypatch.setitem(sys.modules, "torch", torch_module)
    monkeypatch.setitem(sys.modules, "chatterbox", chatterbox_package)
    monkeypatch.setitem(sys.modules, "chatterbox.mtl_tts", chatterbox_module)
    monkeypatch.setitem(sys.modules, "huggingface_hub", huggingface_module)

    tts = ChatterboxTextToSpeech(
        device="auto",
        reference_audio=tmp_path / "unused.wav",
    )

    loaded_model, device = tts._load_model()

    assert loaded_model is model
    assert device == "cuda"

    snapshot_call = calls["snapshot"]
    assert snapshot_call["repo_id"] == "ResembleAI/chatterbox"
    assert snapshot_call["revision"] == "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18"
    assert "t3_mtl23ls_v2.safetensors" in snapshot_call["allow_patterns"]
    assert "t3_mtl23ls_v3.safetensors" not in snapshot_call["allow_patterns"]

    checkpoint_dir, loader_options = calls["from_local"]
    assert checkpoint_dir == checkpoint
    assert loader_options == {
        "device": "cuda",
        "use_bnb_quantization": True,
        "quantization_bits": 4,
    }


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

