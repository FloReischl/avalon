from avalo_backend.config import settings


def test_local_api_address_is_fixed() -> None:
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8095


def test_gemma_audio_limit_is_recorded() -> None:
    assert settings.audio_max_seconds == 30

