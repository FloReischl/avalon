from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.workflows_config import load_workflows_config


WORKFLOW_FILE = Path(__file__).resolve().parents[1] / "data" / "test-workflow.py"


def write_config(path: Path, workflows: list[dict[str, str]]) -> Path:
    path.write_text(yaml.safe_dump({"workflows": workflows}), encoding="utf-8")
    return path


def test_loads_registered_test_workflow(tmp_path: Path) -> None:
    config = load_workflows_config(
        write_config(tmp_path / "workflows.yaml", [{"key": "test-workflow", "file_path": str(WORKFLOW_FILE)}])
    )

    assert config.get("test-workflow").file_path == WORKFLOW_FILE.resolve()


def test_unknown_workflow_key_is_not_resolved(tmp_path: Path) -> None:
    config = load_workflows_config(
        write_config(tmp_path / "workflows.yaml", [{"key": "test-workflow", "file_path": str(WORKFLOW_FILE)}])
    )

    with pytest.raises(KeyError, match="unknown"):
        config.get("unknown")


def test_duplicate_workflow_keys_are_invalid(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="Workflow keys must be unique"):
        load_workflows_config(
            write_config(
                tmp_path / "workflows.yaml",
                [
                    {"key": "test-workflow", "file_path": str(WORKFLOW_FILE)},
                    {"key": "test-workflow", "file_path": str(WORKFLOW_FILE)},
                ],
            )
        )


def test_missing_workflow_file_is_invalid(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="Workflow file is missing"):
        load_workflows_config(
            write_config(
                tmp_path / "workflows.yaml",
                [{"key": "missing", "file_path": str(tmp_path / "missing.py")}],
            )
        )
