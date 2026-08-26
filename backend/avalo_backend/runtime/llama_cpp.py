"""Planned llama.cpp runtime adapter."""

from pathlib import Path


class LlamaCppRuntime:
    """Stub for the runtime selected by the Gemma 4 spike."""

    async def health(self) -> bool:
        raise NotImplementedError("llama.cpp health check is not implemented yet.")

    async def generate_text(self, message: str) -> str:
        del message
        raise NotImplementedError("llama.cpp text generation is not implemented yet.")

    async def generate_from_audio(self, audio_file: Path) -> str:
        del audio_file
        raise NotImplementedError("llama.cpp audio generation is not implemented yet.")

