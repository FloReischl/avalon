"""Central backend configuration."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LlmConfig:
    """One selectable Ollama model."""

    key: str
    model: str


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
    llm_models: tuple[LlmConfig, ...] = (
        LlmConfig(
            key="standard",
            model="qwen2.5-coder:14b-instruct-ctx16k",
            # model="qwen2.5-coder:7b-instruct-ctx16k",
            # model="qwen2.5-coder:7b-instruct",
        ),
        LlmConfig(
            key="gemma",
            model="gemma4:e4b-it-q4_K_M-ctx16k",
        ),
        LlmConfig(
            key="qwen",
            model="qwen2.5-coder:7b-instruct-ctx16k",
            # model="qwen2.5-coder:7b-instruct",
        ),
        LlmConfig(
            key="uncensored",
            model="hf.co/mradermacher/NeuralDaredevil-8B-abliterated-GGUF:Q4_K_M",
        ),
        LlmConfig(
            key="nsfw",
            model="hf.co/mradermacher/L3-8B-Stheno-v3.2-GGUF:Q4_K_M",
        ),
    )
    tts_engine: str = "kokoro"
    tts_device: str = "auto"

    tts_chatterbox_reference_audio: str = "data/tts/chatterbox/frieda1.wav"
    tts_chatterbox_model_revision: str = "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18"

    tts_idle_unload_seconds: float = 300.0

    @property
    def ollama_model(self) -> str:
        """Return the standard model until runtime selection moves to AvalonState."""
        return next(
            llm.model
            for llm in self.llm_models
            if llm.key == "standard"
        )


settings = Settings()

_llm_keys = [llm.key for llm in settings.llm_models]
if len(_llm_keys) != len(set(_llm_keys)):
    raise ValueError("LLM keys must be unique.")
if "standard" not in _llm_keys:
    raise ValueError("Required LLM 'standard' is missing.")
