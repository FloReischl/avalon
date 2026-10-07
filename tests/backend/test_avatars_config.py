from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

import app.avatars_config as avatars_config_module
from app.avatars_config import initialize_avatars_config, load_avatars_config


def valid_avatars(tmp_path: Path) -> dict:
    avatar_dir = tmp_path / "avatar"
    avatar_dir.mkdir()
    for name in ("standard.png", "listening.png", "speaking.png", "thinking.png"):
        (avatar_dir / name).write_bytes(b"asset")
    animations = [
        {"key": key, "category": "state", "sprite-set": f"{key}.png", "sprites": [[0, 0, 10, 20]]}
        for key in ("listening", "speaking", "thinking")
    ]
    return {"avatars": [{"key": "standard", "base_path": str(avatar_dir), "greeting_audio": "greeting.wav", "images": {"standard": "standard.png", "animations": animations}}]}


def write_avatars(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_loads_valid_avatars_config(tmp_path: Path) -> None:
    path = tmp_path / "avatars.yaml"
    write_avatars(path, valid_avatars(tmp_path))
    config = load_avatars_config(path)
    assert config.standard_avatar.key == "standard"
    assert config.standard_avatar.images.animations[0].sprites[0].width == 10


@pytest.mark.parametrize("content", ["avatars: [", "avatars: []"])
def test_invalid_avatars_config_is_fatal(tmp_path: Path, content: str) -> None:
    path = tmp_path / "avatars.yaml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises((yaml.YAMLError, ValidationError)):
        load_avatars_config(path)


def test_missing_avatars_config_is_fatal(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_avatars_config(tmp_path / "missing.yaml")


def test_standard_avatar_is_required(tmp_path: Path) -> None:
    data = valid_avatars(tmp_path)
    data["avatars"][0]["key"] = "other"
    path = tmp_path / "avatars.yaml"
    write_avatars(path, data)
    with pytest.raises(ValidationError, match="Required avatar 'standard' is missing"):
        load_avatars_config(path)


def test_avatar_keys_must_be_unique(tmp_path: Path) -> None:
    data = valid_avatars(tmp_path)
    data["avatars"].append(deepcopy(data["avatars"][0]))
    path = tmp_path / "avatars.yaml"
    write_avatars(path, data)
    with pytest.raises(ValidationError, match="Avatar keys must be unique"):
        load_avatars_config(path)


def test_avatar_assets_are_validated(tmp_path: Path) -> None:
    data = valid_avatars(tmp_path)
    data["avatars"][0]["images"]["animations"][0]["sprite-set"] = "../outside.png"
    path = tmp_path / "avatars.yaml"
    write_avatars(path, data)
    with pytest.raises(ValidationError, match="resolves outside base_path"):
        load_avatars_config(path)


def test_animation_validation_is_preserved(tmp_path: Path) -> None:
    data = valid_avatars(tmp_path)
    animations = data["avatars"][0]["images"]["animations"]
    animations.append(deepcopy(animations[0]))
    path = tmp_path / "avatars.yaml"
    write_avatars(path, data)
    with pytest.raises(ValidationError, match="Animation keys must be unique"):
        load_avatars_config(path)


def test_required_animation_validation_is_preserved(tmp_path: Path) -> None:
    data = valid_avatars(tmp_path)
    data["avatars"][0]["images"]["animations"] = data["avatars"][0]["images"]["animations"][:2]
    path = tmp_path / "avatars.yaml"
    write_avatars(path, data)
    with pytest.raises(ValidationError, match="Required avatar animations are missing: thinking"):
        load_avatars_config(path)


def test_missing_declared_avatar_asset_is_fatal(tmp_path: Path) -> None:
    data = valid_avatars(tmp_path)
    (tmp_path / "avatar" / "thinking.png").unlink()
    path = tmp_path / "avatars.yaml"
    write_avatars(path, data)
    with pytest.raises(ValidationError, match="Avatar asset is missing"):
        load_avatars_config(path)


def test_missing_greeting_audio_is_allowed(tmp_path: Path) -> None:
    path = tmp_path / "avatars.yaml"
    write_avatars(path, valid_avatars(tmp_path))
    config = load_avatars_config(path)
    assert not (config.standard_avatar.base_path / config.standard_avatar.greeting_audio).exists()


def test_avatars_config_is_initialized_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "avatars.yaml"
    write_avatars(path, valid_avatars(tmp_path))
    monkeypatch.setattr(avatars_config_module, "_avatars_config", None)
    first = initialize_avatars_config(path)
    path.write_text("invalid: [", encoding="utf-8")
    assert initialize_avatars_config(path) is first
