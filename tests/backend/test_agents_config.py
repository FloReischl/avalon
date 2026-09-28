from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.agents_config import load_agents_config


def test_load_agents_config_canonicalizes_nested_scope_key_order(tmp_path: Path) -> None:
    path = tmp_path / "agents.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "agents": [
                    {
                        "name": "Hedwig",
                        "key": "podcast",
                        "persona": "Persona",
                        "instructions": "Instructions",
                        "permissions": [
                            {
                                "permission_catalog": {"context": "file", "key": "copy"},
                                "principal_permission": {
                                    "scope": [{"destination": "b", "source": "a"}],
                                    "validity_type": "duration",
                                    "default_expiry": 7200,
                                },
                            }
                        ],
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    config = load_agents_config(path)

    assert config.agents[0].permissions[0].principal_permission.canonical_scope == (
        '[{"destination":"b","source":"a"}]'
    )


def test_duplicate_agent_permission_identity_is_invalid(tmp_path: Path) -> None:
    path = tmp_path / "agents.yaml"
    permission = {
        "permission_catalog": {"context": "web", "key": "search"},
        "principal_permission": {
            "scope": [], "validity_type": "duration", "default_expiry": 1
        },
    }
    path.write_text(
        yaml.safe_dump(
            {"agents": [{"name": "A", "key": "a", "persona": "P", "instructions": "I", "permissions": [permission, permission]}]},
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="Permission identities must be unique"):
        load_agents_config(path)
