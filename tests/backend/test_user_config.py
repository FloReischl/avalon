from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

import app.user_config as user_config_module
from app.user_config import initialize_user_config, load_user_config


def _valid_config(tmp_path: Path) -> tuple[dict, Path]:
    avatar_dir = tmp_path / "avatar"
    avatar_dir.mkdir()

    for name in (
        "standard.png",
        "listening.png",
        "speaking.png",
        "thinking.png",
        "bend-forward.png",
    ):
        (avatar_dir / name).write_bytes(b"asset")

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
        "avatars": [
            {
                "key": "standard",
                "persona": "Friendly.",
                "instructions": "Answer briefly.",
                "base_path": str(avatar_dir),
                "greeting_audio": "greeting.wav",
                "images": {
                    "standard": "standard.png",
                    "animations": [
                        {
                            "key": "listening",
                            "category": "state",
                            "sprite-set": "listening.png",
                            "sprites": [[0, 0, 10, 20]],
                        },
                        {
                            "key": "speaking",
                            "category": "state",
                            "sprite-set": "speaking.png",
                            "sprites": [[10, 0, 10, 20]],
                        },
                        {
                            "key": "thinking",
                            "category": "state",
                            "sprite-set": "thinking.png",
                            "sprites": [[20, 0, 10, 20]],
                        },
                        {
                            "key": "bend-forward",
                            "category": "custom",
                            "sprite-set": "bend-forward.png",
                            "sprites": [[30, 0, 10, 20]],
                        },
                    ],
                },
            },
        ],
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
    assert config.standard_avatar.key == "standard"
    assert config.standard_avatar.base_path == (tmp_path / "avatar").resolve()
    assert config.standard_avatar.greeting_audio == "greeting.wav"
    assert config.tts.kokoro.model == (tmp_path / "tts" / "model.pth").resolve()
    assert config.standard_avatar.images.animations[0].sprites[0].width == 10


def test_missing_user_config_is_fatal(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_user_config(tmp_path / "missing.yaml")


def test_invalid_yaml_is_fatal(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("avatars: [", encoding="utf-8")

    with pytest.raises(yaml.YAMLError):
        load_user_config(config_path)


def test_standard_avatar_is_required(tmp_path: Path) -> None:
    data, config_path = _valid_config(tmp_path)
    data["avatars"][0]["key"] = "other"
    _write_config(config_path, data)

    with pytest.raises(
        ValidationError,
        match="Required avatar 'standard' is missing",
    ):
        load_user_config(config_path)


def test_avatar_keys_must_be_unique(tmp_path: Path) -> None:
    data, config_path = _valid_config(tmp_path)
    data["avatars"].append(deepcopy(data["avatars"][0]))
    _write_config(config_path, data)

    with pytest.raises(ValidationError, match="Avatar keys must be unique"):
        load_user_config(config_path)


def test_animation_keys_must_be_unique(tmp_path: Path) -> None:
    data, config_path = _valid_config(tmp_path)
    animations = data["avatars"][0]["images"]["animations"]
    animations.append(deepcopy(animations[0]))
    _write_config(config_path, data)

    with pytest.raises(
        ValidationError,
        match="Animation keys must be unique within one avatar",
    ):
        load_user_config(config_path)


def test_standard_animation_key_is_forbidden(tmp_path: Path) -> None:
    data, config_path = _valid_config(tmp_path)
    data["avatars"][0]["images"]["animations"][3]["key"] = "standard"
    _write_config(config_path, data)

    with pytest.raises(
        ValidationError,
        match="Animation key 'standard' is reserved",
    ):
        load_user_config(config_path)


def test_required_state_animation_keys_must_exist(tmp_path: Path) -> None:
    data, config_path = _valid_config(tmp_path)
    animations = data["avatars"][0]["images"]["animations"]
    data["avatars"][0]["images"]["animations"] = [
        animation
        for animation in animations
        if animation["key"] != "thinking"
    ]
    _write_config(config_path, data)

    with pytest.raises(
        ValidationError,
        match="Required avatar animations are missing: thinking",
    ):
        load_user_config(config_path)


def test_invalid_sprite_region_is_fatal(tmp_path: Path) -> None:
    data, config_path = _valid_config(tmp_path)
    data["avatars"][0]["images"]["animations"][0]["sprites"][0] = [
        -1,
        0,
        10,
        20,
    ]
    _write_config(config_path, data)

    with pytest.raises(ValidationError):
        load_user_config(config_path)


def test_missing_declared_avatar_asset_is_fatal(tmp_path: Path) -> None:
    data, config_path = _valid_config(tmp_path)
    (tmp_path / "avatar" / "thinking.png").unlink()
    _write_config(config_path, data)

    with pytest.raises(ValidationError, match="Avatar asset is missing"):
        load_user_config(config_path)


def test_missing_greeting_audio_is_allowed_at_config_load(
    tmp_path: Path,
) -> None:
    data, config_path = _valid_config(tmp_path)
    _write_config(config_path, data)

    config = load_user_config(config_path)

    assert config.standard_avatar.greeting_audio == "greeting.wav"
    assert not (
        config.standard_avatar.base_path
        / config.standard_avatar.greeting_audio
    ).exists()


def test_avatar_asset_must_stay_inside_base_path(tmp_path: Path) -> None:
    data, config_path = _valid_config(tmp_path)
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"outside")
    data["avatars"][0]["images"]["animations"][0]["sprite-set"] = "../outside.png"
    _write_config(config_path, data)

    with pytest.raises(
        ValidationError,
        match="resolves outside base_path",
    ):
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
