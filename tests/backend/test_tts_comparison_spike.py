import sys
from pathlib import Path
import wave

SPIKE_ROOT = Path(__file__).resolve().parents[2] / "spikes" / "tts_comparison"
sys.path.insert(0, str(SPIKE_ROOT.parent))

from tts_comparison.run import load_json, matrix, validate_wav  # noqa: E402


def test_fixed_matrix_has_each_engine_for_each_text():
    config = load_json(SPIKE_ROOT / "config.json")
    texts = load_json(SPIKE_ROOT / "texts.json")

    assert {(engine, text["id"]) for engine, text in matrix(config, texts)} == {
        ("piper", "news"), ("piper", "suspense"), ("piper", "erotic"),
        ("kokoro_victoria", "news"), ("kokoro_victoria", "suspense"), ("kokoro_victoria", "erotic"),
        ("kokoro_kerstin", "news"), ("kokoro_kerstin", "suspense"), ("kokoro_kerstin", "erotic"),
    }


def test_validate_wav_accepts_non_empty_mono_audio(tmp_path: Path):
    path = tmp_path / "sample.wav"
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\x01\x00" * 160)

    info = validate_wav(path)

    assert info.channels == 1
    assert info.sample_rate_hz == 16000
    assert info.duration_seconds > 0
