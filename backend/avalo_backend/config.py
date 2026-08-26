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


settings = Settings()
