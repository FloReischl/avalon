"""Administrative per-user configuration of selectable LLMs."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.config import LlmConfig


MODELS_CONFIG_PATH = Path("~/.avalon/models.yaml").expanduser()
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class StrictModelsConfigModel(BaseModel):
    """Reject unknown administrative configuration fields."""

    model_config = ConfigDict(extra="forbid")


class ModelConfig(StrictModelsConfigModel):
    """One explicitly configured selectable Ollama model."""

    key: NonEmptyStr
    model: NonEmptyStr
    tool_support: bool = Field(strict=True)

    def to_llm_config(self) -> LlmConfig:
        return LlmConfig(
            key=self.key,
            model=self.model,
            tool_support=self.tool_support,
        )


class ModelsConfig(StrictModelsConfigModel):
    """Validated administrative LLM catalog."""

    models: list[ModelConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_models(self) -> Self:
        keys = [model.key for model in self.models]
        if len(keys) != len(set(keys)):
            raise ValueError("Model keys must be unique.")
        if "standard" not in keys:
            raise ValueError("Required model 'standard' is missing.")
        return self

    @property
    def llm_models(self) -> tuple[LlmConfig, ...]:
        return tuple(model.to_llm_config() for model in self.models)


_models_config: ModelsConfig | None = None


def load_models_config(path: Path = MODELS_CONFIG_PATH) -> ModelsConfig:
    """Load and fully validate one models configuration file."""
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    return ModelsConfig.model_validate(data)


def initialize_models_config(path: Path = MODELS_CONFIG_PATH) -> ModelsConfig:
    """Load the process-local models configuration exactly once."""
    global _models_config

    if _models_config is None:
        _models_config = load_models_config(path)
    return _models_config


def get_models_config() -> ModelsConfig:
    """Return the initialized process-local models configuration."""
    if _models_config is None:
        raise RuntimeError("Models configuration has not been initialized.")
    return _models_config
