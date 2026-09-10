"""Kikiri/Kokoro German text-to-speech adapter."""

from __future__ import annotations

import asyncio
import gc
from io import BytesIO
from pathlib import Path
from typing import Any

import regex

from app.config import settings
from app.user_config import get_user_config


_SAMPLE_RATE_HZ = 24000

_EMOJI_PATTERN = regex.compile(
    r"(?:"
    r"\p{Regional_Indicator}{1,2}"
    r"|[0-9#*]\uFE0F?\u20E3"
    r"|\p{Extended_Pictographic}"
    r"(?:\uFE0F|\p{Emoji_Modifier})?"
    r"(?:\u200D\p{Extended_Pictographic}"
    r"(?:\uFE0F|\p{Emoji_Modifier})?)+"
    r"|\p{Extended_Pictographic}\uFE0F"
    r"(?:\p{Emoji_Modifier})?"
    r"|\p{Emoji_Presentation}"
    r"(?:\p{Emoji_Modifier})?"
    r")"
)


def _remove_emojis(text: str) -> str:
    return _EMOJI_PATTERN.sub("", text)


class KokoroTextToSpeech:
    """Generate German WAV audio using the local Victoria Kikiri/Kokoro model."""

    def __init__(
        self,
        *,
        device: str | None = None,
        model_path: Path | None = None,
        voice_path: Path | None = None,
        config_path: Path | None = None,
    ) -> None:
        self._requested_device = device or settings.tts_device
        self._model_path = model_path
        self._voice_path = voice_path
        self._config_path = config_path


        self._model: Any | None = None
        self._pipeline: Any | None = None
        self._voice: Any | None = None
        self._device: str | None = None

    async def synthesize(self, text: str) -> bytes:
        """Generate one complete WAV response without creating a temporary file."""
        text = _remove_emojis(text)

        if not text.strip():
            raise ValueError("TTS text must not be empty.")

        return await asyncio.to_thread(self._synthesize_sync, text)

    async def unload(self) -> None:
        """Release the loaded model, pipeline, voice and cached CUDA memory."""
        await asyncio.to_thread(self._unload_sync)

    def _synthesize_sync(self, text: str) -> bytes:
        try:
            import numpy as np
            import soundfile as sf

            _, pipeline, voice = self._ensure_runtime()

            chunks = [
                audio
                for _, _, audio in pipeline(
                    text,
                    voice=voice,
                    speed=1,
                )
            ]

            if not chunks:
                raise RuntimeError("Kokoro produced no audio chunks.")

            output = BytesIO()
            sf.write(
                output,
                np.concatenate(chunks),
                _SAMPLE_RATE_HZ,
                format="WAV",
            )
            audio = output.getvalue()
        except Exception as error:
            raise RuntimeError(
                f"Kokoro synthesis failed: {error}"
            ) from error

        if not audio:
            raise RuntimeError("Kokoro produced empty audio.")

        return audio

    def _ensure_runtime(self) -> tuple[Any, Any, Any]:
        if (
            self._model is None
            or self._pipeline is None
            or self._voice is None
        ):
            (
                self._model,
                self._pipeline,
                self._voice,
                self._device,
            ) = self._load_runtime()

        return self._model, self._pipeline, self._voice

    def _load_runtime(self) -> tuple[Any, Any, Any, str]:
        if (
            self._model_path is None
            or self._voice_path is None
            or self._config_path is None
        ):
            kokoro_config = get_user_config().tts.kokoro
            self._model_path = self._model_path or kokoro_config.model
            self._voice_path = self._voice_path or kokoro_config.voice
            self._config_path = self._config_path or kokoro_config.config

        for description, path in (

            ("model", self._model_path),
            ("voice", self._voice_path),
            ("config", self._config_path),
        ):
            if not path.is_file():
                raise RuntimeError(
                    f"Kokoro {description} artifact is missing: {path}"
                )

        try:
            import torch
            from kokoro import KModel, KPipeline
        except ImportError as error:
            raise RuntimeError(
                "Kokoro dependencies are unavailable."
            ) from error

        device = self._requested_device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        if device not in {"cpu", "cuda"}:
            raise RuntimeError(
                f"Unsupported Kokoro device: {device}"
            )

        model = KModel(
            repo_id="hexgrad/Kokoro-82M",
            config=str(self._config_path),
            model=str(self._model_path),
        )
        model = model.to(device).eval()

        pipeline = KPipeline(
            lang_code="d",
            repo_id="hexgrad/Kokoro-82M",
            model=model,
        )

        voice = torch.load(
            self._voice_path,
            map_location="cpu",
            weights_only=True,
        )

        return model, pipeline, voice, device

    def _unload_sync(self) -> None:
        if (
            self._model is None
            and self._pipeline is None
            and self._voice is None
        ):
            return

        device = self._device

        self._model = None
        self._pipeline = None
        self._voice = None
        self._device = None

        gc.collect()

        if device == "cuda":
            import torch

            torch.cuda.empty_cache()
