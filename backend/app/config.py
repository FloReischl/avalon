"""Central backend configuration."""

import logging
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LlmConfig:
    """One selectable Ollama model."""

    key: str
    model: str
    tool_support: bool = False


@dataclass(frozen=True, slots=True)
class Settings:
    """Static settings for the initial local development setup."""

    app_name: str = "Avalon Backend"
    api_host: str = "127.0.0.1"
    api_port: int = 8095
    music_db_path: str = "/media/flo/2TB_SSD/music/mp3db.sqlite3"
    frontend_dev_origin: str = "http://127.0.0.1:5173"
    default_language: str = "de"
    audio_wait_exceed_seconds: float = 1.0
    context_compression_trigger_tokens: int = 8_000
    context_compression_target_tokens: int = 6_000
    context_compression_chars_per_token: int = 3
    context_compression_protected_roundtrips: int = 2
    context_compression_max_attempts: int = 3
    ollama_host: str = "127.0.0.1:11434"
    tts_engine: str = "kokoro"
    tts_device: str = "auto"

    tts_chatterbox_reference_audio: str = "data/tts/chatterbox/frieda1.wav"
    tts_chatterbox_model_revision: str = "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18"

    tts_idle_unload_seconds: float = 300.0
    log_file_path: str = "/tmp/avalon/log.txt"


settings = Settings()


def configure_logging() -> None:
    """Configure root logging to output all infos/errors to both stdout/stderr and log file."""
    log_path = Path(settings.log_file_path).expanduser()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    if not any(isinstance(h, logging.FileHandler) for h in root_logger.handlers):
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in root_logger.handlers):
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)
