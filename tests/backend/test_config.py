from app.config import settings


def test_local_api_address_is_fixed() -> None:
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8095


def test_gemma_audio_limit_is_recorded() -> None:
    assert settings.audio_max_seconds == 30


def test_ollama_runtime_settings_are_recorded() -> None:
    assert settings.ollama_host == "127.0.0.1:11434"
    # assert settings.ollama_model == "hf.co/TrevorJS/gemma-4-E4B-it-uncensored-GGUF:Q4_K_M"
    assert settings.ollama_model == "gemma4:e4b-it-q4_K_M"


def test_chatterbox_tts_settings_are_recorded() -> None:
    assert settings.tts_device == "auto"
    assert settings.tts_reference_audio == "data/chatterbox-frieda1.wav"
    assert (
        settings.tts_model_revision
        == "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18"
    )
    assert settings.tts_idle_unload_seconds == 300.0


