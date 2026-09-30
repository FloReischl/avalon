"""Application service for audio file creation using Kokoro TTS and ffmpeg."""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path

from app.tts.base import TextToSpeech
from app.tts.factory import create_tts_engine


logger = logging.getLogger(__name__)


class AudioCreationService:
    """Synthesize text using TTS and convert WAV to MP3 via ffmpeg."""

    def __init__(self, tts_engine: TextToSpeech | None = None) -> None:
        self._tts_engine = tts_engine

    async def create_audio(self, content: str, output_file: str) -> None:
        """Synthesize text and write output as an MP3 file."""
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Content must be a non-empty string.")

        if not isinstance(output_file, str) or not output_file.lower().endswith(".mp3"):
            raise ValueError("Output file must be a string ending with '.mp3'.")

        target_path = Path(output_file).expanduser()
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            raise RuntimeError(f"Cannot create parent directory for {output_file}: {exc}") from exc

        tts = self._tts_engine or create_tts_engine()
        wav_bytes = await tts.synthesize(content)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_wav_path = Path(temp_wav.name)
            temp_wav.write(wav_bytes)

        temp_mp3_path = target_path.with_suffix(f".tmp.{os.getpid()}.mp3")

        try:
            try:
                process = await asyncio.create_subprocess_exec(
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(temp_wav_path),
                    "-codec:a",
                    "libmp3lame",
                    "-qscale:a",
                    "2",
                    str(temp_mp3_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            except FileNotFoundError as exc:
                raise RuntimeError("ffmpeg is not installed or available in PATH.") from exc

            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="ignore").strip()
                raise RuntimeError(f"ffmpeg failed with exit code {process.returncode}: {error_msg}")

            try:
                temp_mp3_path.replace(target_path)
            except Exception as exc:
                raise RuntimeError(f"Cannot write output MP3 file {output_file}: {exc}") from exc

        finally:
            if temp_wav_path.exists():
                try:
                    temp_wav_path.unlink()
                except Exception:
                    pass
            if temp_mp3_path.exists():
                try:
                    temp_mp3_path.unlink()
                except Exception:
                    pass
