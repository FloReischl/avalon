from app.config import settings
import logging
from pathlib import Path
import pytest

def test_local_api_address_is_fixed() -> None:
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8095
    assert settings.music_db_path == "/media/flo/2TB_SSD/music/mp3db.sqlite3"



def test_ollama_runtime_settings_are_recorded() -> None:
    assert settings.ollama_host == "127.0.0.1:11434"


def test_chatterbox_tts_settings_are_recorded() -> None:
    assert settings.tts_device == "auto"
    assert settings.tts_chatterbox_reference_audio == "data/tts/chatterbox/frieda1.wav"
    assert (
        settings.tts_chatterbox_model_revision
        == "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18"
    )
    assert settings.tts_idle_unload_seconds == 300.0


def test_configure_logging() -> None:
    from app.config import configure_logging
    configure_logging()
    
    root_logger = logging.getLogger()
    has_file = any(isinstance(h, logging.FileHandler) for h in root_logger.handlers)
    has_stream = any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in root_logger.handlers)
    
    assert has_file
    assert has_stream
    
    logger = logging.getLogger("test.avalon.logger")
    logger.info("Test info message for logging configuration")
    
    log_path = Path(settings.log_file_path).expanduser()
    assert log_path.parent.is_dir()


if __name__ == "__main__":
    # Führt alle Tests in genau dieser Datei aus (__file__)
    pytest.main([__file__, "-v", "-s"])
