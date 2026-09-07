"""Chatterbox Multilingual text-to-speech adapter."""

from __future__ import annotations

import asyncio
import gc
from io import BytesIO
from pathlib import Path
from typing import Any

from app.config import settings


PROJECT_ROOT = Path(__file__).resolve().parents[3]

_MODEL_FILENAMES = [
    "ve.pt",
    "t3_mtl23ls_v3.safetensors",
    "s3gen.pt",
    "grapheme_mtl_merged_expanded_v1.json",
    "conds.pt",
    "Cangjie5_TC.json",
]


class ChatterboxTextToSpeech:
    """Generate German WAV audio using Chatterbox Multilingual V3."""

    def __init__(
        self,
        *,
        device: str | None = None,
        reference_audio: Path | None = None,
        model_revision: str | None = None,
    ) -> None:
        self._requested_device = device or settings.tts_device
        self._reference_audio = (
            reference_audio
            if reference_audio is not None
            else PROJECT_ROOT / settings.tts_reference_audio
        )
        self._model_revision = model_revision or settings.tts_model_revision
        self._model: Any | None = None
        self._device: str | None = None

    async def synthesize(self, text: str) -> bytes:
        """Generate one complete WAV response without creating a temporary file."""
        if not text.strip():
            raise ValueError("TTS text must not be empty.")

        return await asyncio.to_thread(self._synthesize_sync, text)

    async def unload(self) -> None:
        """Release the loaded model and cached CUDA memory."""
        await asyncio.to_thread(self._unload_sync)

    def _synthesize_sync(self, text: str) -> bytes:
        if not self._reference_audio.is_file():
            raise RuntimeError(
                f"Chatterbox reference audio is missing: {self._reference_audio}"
            )

        try:
            import torchaudio

            model = self._ensure_model()
            wav = model.generate(
                text,
                language_id=settings.default_language,
                audio_prompt_path=str(self._reference_audio),
            )

            output = BytesIO()
            torchaudio.save(
                output,
                wav.cpu(),
                model.sr,
                format="wav",
            )
            audio = output.getvalue()
        except Exception as error:
            raise RuntimeError("Chatterbox synthesis failed.") from error

        if not audio:
            raise RuntimeError("Chatterbox produced empty audio.")

        return audio

    def _ensure_model(self) -> Any:
        if self._model is None:
            self._model, self._device = self._load_model()

        return self._model

    def _load_model(self) -> tuple[Any, str]:
        try:
            import torch
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS
            from huggingface_hub import snapshot_download
        except ImportError as error:
            raise RuntimeError("Chatterbox dependencies are unavailable.") from error

        device = self._requested_device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        if device not in {"cpu", "cuda"}:
            raise RuntimeError(f"Unsupported Chatterbox device: {device}")

        checkpoint_dir = Path(
            snapshot_download(
                repo_id="ResembleAI/chatterbox",
                revision=self._model_revision,
                allow_patterns=_MODEL_FILENAMES,
            )
        )
        model = ChatterboxMultilingualTTS.from_local(
            checkpoint_dir,
            device=device,
            t3_model="v3",
        )
        return model, device

    def _unload_sync(self) -> None:
        if self._model is None:
            return

        device = self._device
        self._model = None
        self._device = None

        gc.collect()

        if device == "cuda":
            import torch

            torch.cuda.empty_cache()


