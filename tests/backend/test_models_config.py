from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

import app.models_config as models_config_module
from app.models_config import ModelsConfig, get_models_config, initialize_models_config, load_models_config


def write_models(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def valid_models() -> str:
    return "models:\n- key: standard\n  model: test:standard\n  tool_support: true\n"


def test_loads_valid_models_and_tool_support(tmp_path: Path) -> None:
    config = load_models_config(write_models(tmp_path / "models.yaml", valid_models()))
    assert config.llm_models[0].key == "standard"
    assert config.llm_models[0].tool_support is True


def test_missing_file_is_fatal(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_models_config(tmp_path / "missing.yaml")


@pytest.mark.parametrize("content", ["models: [", "models: []", "models:\n- model: x\n  tool_support: true", "models:\n- key: standard\n  tool_support: true", "models:\n- key: standard\n  model: x", "models:\n- key: '   '\n  model: x\n  tool_support: true", "models:\n- key: standard\n  model: '   '\n  tool_support: true", "models:\n- key: standard\n  model: x\n  tool_support: true\n- key: standard\n  model: y\n  tool_support: false", "models:\n- key: other\n  model: x\n  tool_support: true", "models:\n- key: standard\n  model: x\n  tool_support: true\n  unknown: value"])
def test_rejects_invalid_models_config(tmp_path: Path, content: str) -> None:
    with pytest.raises((ValidationError, yaml.YAMLError)):
        load_models_config(write_models(tmp_path / "models.yaml", content))


def test_tool_support_must_be_boolean() -> None:
    with pytest.raises(ValidationError):
        ModelsConfig.model_validate({"models": [{"key": "standard", "model": "x", "tool_support": "true"}]})


def test_initialize_once(tmp_path: Path) -> None:
    models_config_module._models_config = None
    first = write_models(tmp_path / "first.yaml", valid_models())
    second = write_models(tmp_path / "second.yaml", valid_models().replace("test:standard", "test:second"))
    initialized = initialize_models_config(first)
    assert initialize_models_config(second) is initialized
    assert get_models_config() is initialized
