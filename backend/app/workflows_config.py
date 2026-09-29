"""Validated static registry for executable Avalon workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_CONFIG_PATH = Path("~/.avalon/workflows.yaml").expanduser()
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class StrictWorkflowsConfigModel(BaseModel):
    """Reject unknown workflow configuration fields."""

    model_config = ConfigDict(extra="forbid")


class WorkflowConfig(StrictWorkflowsConfigModel):
    """One server-owned executable workflow definition."""

    key: NonEmptyStr
    file_path: Path

    @field_validator("file_path", mode="after")
    @classmethod
    def validate_file_path(cls, value: Path) -> Path:
        path = value.expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        path = path.resolve()
        if not path.is_file():
            raise ValueError(f"Workflow file is missing or not a file: {path}")
        if path.suffix != ".py":
            raise ValueError(f"Workflow file must be a Python file: {path}")
        return path


class WorkflowsConfig(StrictWorkflowsConfigModel):
    """Validated registry of server-owned workflow definitions."""

    workflows: list[WorkflowConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_workflow_keys(self) -> Self:
        keys = [workflow.key for workflow in self.workflows]
        if len(keys) != len(set(keys)):
            raise ValueError("Workflow keys must be unique.")
        return self

    def get(self, key: str) -> WorkflowConfig:
        for workflow in self.workflows:
            if workflow.key == key:
                return workflow
        raise KeyError(key)


_workflows_config: WorkflowsConfig | None = None


def load_workflows_config(path: Path = WORKFLOWS_CONFIG_PATH) -> WorkflowsConfig:
    """Load and fully validate the authoritative workflow registry."""
    return WorkflowsConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def initialize_workflows_config(path: Path = WORKFLOWS_CONFIG_PATH) -> WorkflowsConfig:
    """Load the process-local workflow registry exactly once."""
    global _workflows_config
    if _workflows_config is None:
        _workflows_config = load_workflows_config(path)
    return _workflows_config


def get_workflows_config() -> WorkflowsConfig:
    """Return the initialized workflow registry."""
    if _workflows_config is None:
        raise RuntimeError("Workflows configuration has not been initialized.")
    return _workflows_config
