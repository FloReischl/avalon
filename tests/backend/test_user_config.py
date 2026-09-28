from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

import app.user_config as user_config_module
from app.user_config import initialize_user_config, load_user_config


def _valid_config(tmp_path: Path) -> tuple[dict, Path]:
    tts_dir = tmp_path / "tts"
    tts_dir.mkdir()
    model_path = tts_dir / "model.pth"
    voice_path = tts_dir / "voice.pt"
    config_path = tts_dir / "config.json"
    model_path.write_bytes(b"model")
    voice_path.write_bytes(b"voice")
    config_path.write_text("{}", encoding="utf-8")

    data = {
        "name": "Frieda",
        "chat": {"principal_key": "chat-default"},
        "tts": {
            "chatterbox": {
                "reference_audio": str(tmp_path / "missing-chatterbox.wav"),
            },
            "kokoro": {
                "model": str(model_path),
                "voice": str(voice_path),
                "config": str(config_path),
            },
        },
    }

    config_path_yaml = tmp_path / "config.yaml"
    return data, config_path_yaml


def _write_config(path: Path, data: dict) -> None:
    path.write_text(
        yaml.safe_dump(data, sort_keys=False),
        encoding="utf-8",
    )


def test_loads_and_normalizes_valid_user_config(tmp_path: Path) -> None:
    data, config_path = _valid_config(tmp_path)
    _write_config(config_path, data)

    config = load_user_config(config_path)

    assert config.name == "Frieda"
    assert config.chat.principal_key == "chat-default"
    assert config.tts.kokoro.model == (tmp_path / "tts" / "model.pth").resolve()


def test_missing_user_config_is_fatal(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_user_config(tmp_path / "missing.yaml")


def test_invalid_yaml_is_fatal(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("name: [", encoding="utf-8")

    with pytest.raises(yaml.YAMLError):
        load_user_config(config_path)


def test_missing_kokoro_artifact_is_fatal(tmp_path: Path) -> None:
    data, config_path = _valid_config(tmp_path)
    Path(data["tts"]["kokoro"]["model"]).unlink()
    _write_config(config_path, data)

    with pytest.raises(
        ValidationError,
        match="Kokoro model artifact is missing",
    ):
        load_user_config(config_path)


def test_missing_inactive_chatterbox_artifact_is_allowed(
    tmp_path: Path,
) -> None:
    data, config_path = _valid_config(tmp_path)
    _write_config(config_path, data)

    config = load_user_config(config_path)

    assert config.tts.chatterbox is not None
    assert not config.tts.chatterbox.reference_audio.is_file()


def test_user_config_is_initialized_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data, config_path = _valid_config(tmp_path)
    _write_config(config_path, data)
    monkeypatch.setattr(user_config_module, "_user_config", None)

    first = initialize_user_config(config_path)
    config_path.write_text("invalid: [", encoding="utf-8")
    second = initialize_user_config(config_path)

    assert second is first
