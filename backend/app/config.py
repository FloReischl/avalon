"""Central backend configuration."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Static settings for the initial local development setup."""

    app_name: str = "Avalo Backend"
    api_host: str = "127.0.0.1"
    api_port: int = 8095
    frontend_dev_origin: str = "http://127.0.0.1:5173"
    default_language: str = "de"
    audio_max_seconds: int = 30
    audio_wait_exceed_seconds: float = 1.0
    ollama_host: str = "127.0.0.1:11434"
    # ollama_model: str = "gemma4:e4b-it-q4_K_M"
    ollama_model: str = "gemma4:e4b-it-q4_K_M-ctx32k"
    tts_engine: str = "kokoro"
    tts_device: str = "auto"

    tts_chatterbox_reference_audio: str = "data/tts/chatterbox/frieda1.wav"
    tts_chatterbox_model_revision: str = "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18"

    tts_idle_unload_seconds: float = 300.0




settings = Settings()
