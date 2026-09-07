#!/usr/bin/env python3
"""Render the fixed Piper-versus-Kikiri German TTS comparison locally."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import traceback
import wave
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from urllib.request import urlretrieve

ROOT = Path(__file__).resolve().parents[2]
SPIKE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class WavInfo:
    channels: int
    sample_rate_hz: int
    sample_width_bytes: int
    frames: int
    duration_seconds: float
    size_bytes: int


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def matrix(config: dict[str, Any], texts: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [(engine, text) for engine in config["engines"] for text in texts["texts"]]


def validate_wav(path: Path) -> WavInfo:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"WAV fehlt oder ist leer: {path}")
    try:
        with wave.open(str(path), "rb") as audio:
            channels = audio.getnchannels()
            sample_rate = audio.getframerate()
            width = audio.getsampwidth()
            frames = audio.getnframes()
            payload = audio.readframes(frames)
    except wave.Error as error:
        raise ValueError(f"Ungültige WAV-Datei {path}: {error}") from error
    if channels < 1 or sample_rate < 1 or width < 1 or frames < 1:
        raise ValueError(f"WAV ohne gültige Audioeigenschaften: {path}")
    if not any(payload):
        raise ValueError(f"WAV enthält nur Stille: {path}")
    return WavInfo(channels, sample_rate, width, frames, frames / sample_rate, path.stat().st_size)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_files(engine: str, spec: dict[str, Any], model_dir: Path) -> dict[str, Path]:
    destination = model_dir / engine
    destination.mkdir(parents=True, exist_ok=True)
    result: dict[str, Path] = {}
    for item in spec["files"]:
        if "local_path" in item:
            path = ROOT / item["local_path"]
            if not path.is_file():
                raise RuntimeError(f"Lokaler Modellbestandteil fehlt: {path}")
            result[item["name"]] = path
            continue
        path = destination / item["name"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            print(f"Lade {engine}-Modellbestandteil: {item['name']}")
            try:
                urlretrieve(item["url"], path)
            except Exception as error:
                path.unlink(missing_ok=True)
                raise RuntimeError(f"Download fehlgeschlagen: {item['url']}: {error}") from error
        result[item["name"]] = path
    return result


def render_piper(text: str, output: Path, files: dict[str, Path]) -> None:
    command = [sys.executable, "-m", "piper", "--model", str(files["de_DE-kerstin-low.onnx"]), "--output_file", str(output)]
    try:
        subprocess.run(command, input=text, text=True, check=True, capture_output=True)
    except FileNotFoundError as error:
        raise RuntimeError("Piper fehlt. Installiere zuerst requirements.txt dieses Spikes.") from error
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"Piper-Synthese fehlgeschlagen: {error.stderr.strip()}") from error


def select_device(requested: str) -> str:
    if requested in {"cpu", "cuda"}:
        return requested
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def render_kokoro(text: str, output: Path, files: dict[str, Path], requested_device: str, voice_filename: str) -> str:
    try:
        import numpy as np
        import soundfile as sf
        import torch
        from kokoro import KModel, KPipeline
    except ImportError as error:
        raise RuntimeError("Kikiri/Kokoro fehlt. Installiere zuerst requirements.txt dieses Spikes.") from error
    device = select_device(requested_device)
    model = KModel(repo_id="hexgrad/Kokoro-82M", config=str(files["config.json"]), model=str(files["kikiri_german_victoria_ep10.pth"]))
    model = model.to(device).eval()
    pipeline = KPipeline(lang_code="d", repo_id="hexgrad/Kokoro-82M", model=model)
    voice = torch.load(files[voice_filename], map_location="cpu", weights_only=True)
    chunks = [audio for _, _, audio in pipeline(text, voice=voice, speed=1)]
    if not chunks:
        raise RuntimeError("Kikiri/Kokoro hat keine Audiodaten erzeugt.")
    sf.write(str(output), np.concatenate(chunks), 24000)
    return device


def load_chatterbox(requested_device: str):
    try:
        import torchaudio
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        from huggingface_hub import snapshot_download
    except ImportError as error:
        raise RuntimeError("Chatterbox fehlt. Installiere zuerst requirements.txt dieses Spikes.") from error
    device = select_device(requested_device)
    revision = "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18"
    filenames = ["ve.pt", "t3_mtl23ls_v3.safetensors", "s3gen.pt", "grapheme_mtl_merged_expanded_v1.json", "conds.pt", "Cangjie5_TC.json"]
    checkpoint_dir = Path(snapshot_download(repo_id="ResembleAI/chatterbox", revision=revision, allow_patterns=filenames))
    model = ChatterboxMultilingualTTS.from_local(checkpoint_dir, device=device, t3_model="v3")
    return model, device, {name: checkpoint_dir / name for name in filenames}


def render_chatterbox(model, text: str, output: Path, reference: Path) -> None:
    import torchaudio
    wav = model.generate(text, language_id="de", audio_prompt_path=str(reference))
    torchaudio.save(str(output), wav.cpu(), model.sr)


def installed_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def write_rating_template(output_dir: Path, rows: list[dict[str, Any]]) -> Path:
    path = output_dir / "hearing-review.md"
    lines = ["# Hörbewertung: Piper vs. Kikiri/Kokoro", "", "Keine automatische Gewinnerauswahl. Bitte jede Datei separat anhören.", ""]
    for row in rows:
        relative = Path(row["file"]).name
        lines.extend([f"## {row['engine']} – {row['text_id']}", "", f"Datei: [{relative}]({relative})", "", "- Verständlichkeit:", "- Natürlichkeit:", "- Ausdruck:", "- Störende Artefakte:", "- Gesamteindruck:", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=SPIKE_DIR / "config.json")
    args = parser.parse_args()
    config = load_json(args.config)
    texts = load_json(SPIKE_DIR / "texts.json")
    output_dir = ROOT / config["output_dir"]
    model_dir = output_dir / "models"
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {engine: download_files(engine, spec, model_dir) for engine, spec in config["engines"].items()}
    chatterbox_model = chatterbox_device = chatterbox_files = None
    rows: list[dict[str, Any]] = []
    actual_device = "not-used"
    try:
        for engine, text in matrix(config, texts):
            output = output_dir / f"{engine}-{text['id']}.wav"
            output.unlink(missing_ok=True)
            started = time.perf_counter()
            if engine == "piper":
                render_piper(text["text"], output, files[engine])
                device = "cpu (Piper ONNX Runtime default)"
            elif engine in {"kokoro_victoria", "kokoro_kerstin"}:
                shared_files = files["kokoro_victoria"] | files[engine]
                voice_filename = "victoria.pt" if engine == "kokoro_victoria" else "df_kerstin.pt"
                device = render_kokoro(text["text"], output, shared_files, config["device"], voice_filename)
            elif engine == "chatterbox":
                if chatterbox_model is None:
                    chatterbox_model, chatterbox_device, chatterbox_files = load_chatterbox(config["device"])
                render_chatterbox(chatterbox_model, text["text"], output, files[engine]["chatterbox-frieda1.wav"])
                device = chatterbox_device
            else:
                raise RuntimeError(f"Unbekannte Engine: {engine}")
            info = validate_wav(output)
            actual_device = device
            rows.append({"engine": engine, "text_id": text["id"], "text": text["text"], "file": str(output), "render_seconds": round(time.perf_counter() - started, 3), "device": device, "wav": asdict(info)})
    except Exception as error:
        raise SystemExit(
            f"TTS-Spike fehlgeschlagen; kein vollständiger Erfolg: {error}\n\n"
            f"Chatterbox-/Engine-Traceback:\n{traceback.format_exc()}"
        ) from error
    report = {
        "status": "success",
        "run_at_epoch_seconds": time.time(),
        "platform": platform.platform(),
        "python": sys.version,
        "requested_device": config["device"],
        "used_device": actual_device,
        "dependencies": {name: installed_version(name) for name in ("piper-tts", "kokoro-deutsch", "chatterbox-tts", "torch", "soundfile", "numpy")},
        "engines": config["engines"],
        "model_files": {engine: {name: {"path": str(path), "size_bytes": path.stat().st_size, "sha256": sha256(path)} for name, path in entries.items()} for engine, entries in files.items()},
        "renders": rows,
    }
    if chatterbox_files:
        report["model_files"]["chatterbox_weights"] = {name: {"path": str(path), "size_bytes": path.stat().st_size, "sha256": sha256(path)} for name, path in chatterbox_files.items()}
    (output_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_rating_template(output_dir, rows)
    print(f"Erfolgreich: {len(rows)} WAV-Dateien in {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
