"""Validated agent and permission configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints, model_validator


AGENTS_CONFIG_PATH = Path("~/.avalon/agents.yaml").expanduser()
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class StrictAgentsConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PermissionCatalogConfig(StrictAgentsConfigModel):
    context: NonEmptyStr
    key: NonEmptyStr


class PrincipalPermissionConfig(StrictAgentsConfigModel):
    scope: JsonValue = Field(default_factory=list)
    validity_type: Literal["permanent", "duration", "range"]
    default_expiry: int = Field(ge=0)

    @property
    def canonical_scope(self) -> str:
        """Persist scope as stable JSON while deliberately preserving its semantics."""
        return json.dumps(
            self.scope, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )


class AgentPermissionConfig(StrictAgentsConfigModel):
    permission_catalog: PermissionCatalogConfig
    principal_permission: PrincipalPermissionConfig


class AgentConfig(StrictAgentsConfigModel):
    name: NonEmptyStr
    key: NonEmptyStr
    persona: NonEmptyStr
    instructions: NonEmptyStr
    permissions: list[AgentPermissionConfig] = Field(default_factory=list)


class AgentsConfig(StrictAgentsConfigModel):
    agents: list[AgentConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_identities(self) -> Self:
        agent_keys = [agent.key for agent in self.agents]
        if len(agent_keys) != len(set(agent_keys)):
            raise ValueError("Agent keys must be unique.")
        for agent in self.agents:
            identities = [
                (
                    permission.permission_catalog.context,
                    permission.permission_catalog.key,
                    permission.principal_permission.canonical_scope,
                )
                for permission in agent.permissions
            ]
            if len(identities) != len(set(identities)):
                raise ValueError(
                    f"Permission identities must be unique for agent '{agent.key}'."
                )
        return self


def load_agents_config(path: Path = AGENTS_CONFIG_PATH) -> AgentsConfig:
    """Load and fully validate the authoritative agent configuration."""
    raw = path.read_text(encoding="utf-8")
    return AgentsConfig.model_validate(yaml.safe_load(raw))
