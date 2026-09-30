"""Tests for AudioCreationService."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from app.services.audio_creation import AudioCreationService


class FakeTTS:
    def __init__(self, wav_bytes: bytes = b"RIFF....WAVE", error: Exception | None = None) -> None:
        self.wav_bytes = wav_bytes
        self.error = error
        self.synthesized_texts: list[str] = []

    async def synthesize(self, text: str) -> bytes:
        self.synthesized_texts.append(text)
        if self.error:
            raise self.error
        return self.wav_bytes

    async def unload(self) -> None:
        pass


@pytest.mark.asyncio
async def test_create_audio_validates_content_and_extension() -> None:
    service = AudioCreationService(FakeTTS())  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Content must be a non-empty string."):
        await service.create_audio("", "/tmp/test.mp3")

    with pytest.raises(ValueError, match="Content must be a non-empty string."):
        await service.create_audio("   ", "/tmp/test.mp3")

    with pytest.raises(ValueError, match="Output file must be a string ending with '.mp3'."):
        await service.create_audio("Hello", "/tmp/test.wav")


@pytest.mark.asyncio
async def test_create_audio_orchestrates_tts_and_ffmpeg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_file = tmp_path / "sub" / "output.mp3"
    fake_tts = FakeTTS(b"fake-wav-bytes")

    class FakeProcess:
        returncode = 0

        async def communicate(self):
            temp_mp3 = output_file.with_suffix(f".tmp.{os.getpid()}.mp3")
            temp_mp3.parent.mkdir(parents=True, exist_ok=True)
            temp_mp3.write_bytes(b"fake-mp3-bytes")
            return b"", b""

    exec_calls = []

    async def fake_create_subprocess_exec(*args, **kwargs):
        exec_calls.append(args)
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    service = AudioCreationService(fake_tts)  # type: ignore[arg-type]
    await service.create_audio("Hello world", str(output_file))

    assert fake_tts.synthesized_texts == ["Hello world"]
    assert len(exec_calls) == 1
    assert exec_calls[0][0] == "ffmpeg"
    assert exec_calls[0][2] == "-i"
    assert output_file.read_bytes() == b"fake-mp3-bytes"


@pytest.mark.asyncio
async def test_create_audio_handles_ffmpeg_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_file = tmp_path / "output.mp3"
    fake_tts = FakeTTS(b"fake-wav-bytes")

    class FakeProcess:
        returncode = 1

        async def communicate(self):
            return b"", b"ffmpeg error output"

    async def fake_create_subprocess_exec(*args, **kwargs):
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    service = AudioCreationService(fake_tts)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="ffmpeg failed with exit code 1: ffmpeg error output"):
        await service.create_audio("Hello", str(output_file))

    assert not output_file.exists()
