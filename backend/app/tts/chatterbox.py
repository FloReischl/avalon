"""Chatterbox Multilingual text-to-speech adapter."""

from __future__ import annotations

import asyncio
import gc
import re
from io import BytesIO
from pathlib import Path
from typing import Any

from app.config import settings


PROJECT_ROOT = Path(__file__).resolve().parents[3]

_MODEL_FILENAMES = [
    "ve.pt",
    "t3_mtl23ls_v2.safetensors",
    "s3gen.pt",
    "grapheme_mtl_merged_expanded_v1.json",
    "conds.pt",
    "Cangjie5_TC.json",
]

_MAX_CHUNK_CHARS = 300
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_CLAUSE_BOUNDARY = re.compile(r"(?<=[,;:])\s+")


class ChatterboxTextToSpeech:
    """Generate German WAV audio using 4-bit Chatterbox Multilingual V2."""

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
            else PROJECT_ROOT / settings.tts_chatterbox_reference_audio
        )
        self._model_revision = model_revision or settings.tts_chatterbox_model_revision
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
            import torch
            import torchaudio

            model = self._ensure_model()
            wav_chunks = []

            for chunk in self._split_text(text):
                wav = model.generate(
                    chunk,
                    language_id=settings.default_language,
                    audio_prompt_path=str(self._reference_audio),
                )
                wav_chunks.append(wav.cpu())
                del wav

            wav = torch.cat(wav_chunks, dim=-1)

            output = BytesIO()
            torchaudio.save(
                output,
                wav,
                model.sr,
                format="wav",
            )
            audio = output.getvalue()
        except Exception as error:
            raise RuntimeError("Chatterbox synthesis failed.") from error

        if not audio:
            raise RuntimeError("Chatterbox produced empty audio.")

        return audio

    @staticmethod
    def _split_text(text: str) -> list[str]:
        """Split text at natural speech boundaries while bounding TTS chunk size."""
        sentences = [
            sentence.strip()
            for sentence in _SENTENCE_BOUNDARY.split(text.strip())
            if sentence.strip()
        ]

        chunks: list[str] = []
        for sentence in sentences:
            if len(sentence) <= _MAX_CHUNK_CHARS:
                chunks.append(sentence)
                continue

            chunks.extend(
                ChatterboxTextToSpeech._split_long_part(
                    sentence,
                    _CLAUSE_BOUNDARY,
                )
            )

        return chunks

    @staticmethod
    def _split_long_part(text: str, boundary: re.Pattern[str]) -> list[str]:
        parts = [part.strip() for part in boundary.split(text) if part.strip()]
        chunks: list[str] = []

        for part in parts:
            if len(part) <= _MAX_CHUNK_CHARS:
                chunks.append(part)
                continue

            words = part.split()
            current: list[str] = []

            for word in words:
                candidate = " ".join([*current, word])
                if current and len(candidate) > _MAX_CHUNK_CHARS:
                    chunks.append(" ".join(current))
                    current = [word]
                else:
                    current.append(word)

            if current:
                chunks.append(" ".join(current))

        return chunks

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
            use_bnb_quantization=True,
            quantization_bits=4,
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


