from pathlib import Path

import httpx

from app.config import settings
from app.runtime.base import ModelRuntime


class OllamaRuntime(ModelRuntime):
    """Ollama runtime adapter."""

    async def health(self) -> bool:
        """Return whether the configured model is available in Ollama."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://{settings.ollama_host}/api/show",
                    json={"model": settings.ollama_model},
                )
                response.raise_for_status()
                return True
        except (httpx.RequestError, httpx.HTTPStatusError):
            return False

    async def generate_text(self, message: str) -> str:
        """Generate a complete response from text input."""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"http://{settings.ollama_host}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": message,
                        "stream": False,
                    },
                )
                response.raise_for_status()

                data = response.json()
                text = data.get("response")

                if not isinstance(text, str) or not text.strip():
                    raise ValueError("Invalid Ollama response")

                return text
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
            raise RuntimeError(f"Ollama error: {exc}") from exc

    async def generate_from_audio(self, audio_file: Path) -> str:
        """Generate a complete response from native audio input."""
        raise NotImplementedError("Audio generation is not implemented yet.")
