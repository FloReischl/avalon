import json
from pathlib import Path

import pytest

from app.services.workflows import WorkflowExecutionError, WorkflowService
from app.workflows_config import WorkflowsConfig


WORKFLOW_FILE = Path(__file__).resolve().parents[1] / "data" / "test-workflow.py"
OUTPUT_FILE = Path("/tmp/avalon/test-output.txt")


def workflow_config(path: Path = WORKFLOW_FILE) -> WorkflowsConfig:
    return WorkflowsConfig.model_validate(
        {"workflows": [{"key": "test-workflow", "file_path": str(path)}]}
    )


@pytest.mark.asyncio
async def test_executes_registered_workflow_with_json_stdin() -> None:
    OUTPUT_FILE.unlink(missing_ok=True)
    payload = {"message": "Hallo Kenny", "items": [1, True, None]}

    await WorkflowService(workflow_config()).execute("test-workflow", payload)

    output = OUTPUT_FILE.read_text(encoding="utf-8")
    assert json.dumps(payload, ensure_ascii=False, separators=(",", ":")) in output


@pytest.mark.asyncio
async def test_unknown_workflow_does_not_start_a_process(monkeypatch) -> None:
    started = False

    async def create_process(*args, **kwargs):
        nonlocal started
        del args, kwargs
        started = True
        raise AssertionError("must not start")

    monkeypatch.setattr("app.services.workflows.asyncio.create_subprocess_exec", create_process)

    with pytest.raises(WorkflowExecutionError, match="Unknown workflow"):
        await WorkflowService(workflow_config()).execute("unknown", {"value": 1})

    assert not started


@pytest.mark.asyncio
async def test_nonzero_workflow_exit_is_a_controlled_error(tmp_path: Path) -> None:
    failing = tmp_path / "failing.py"
    failing.write_text("import sys\nsys.exit(3)\n", encoding="utf-8")

    with pytest.raises(WorkflowExecutionError, match="exited with code 3"):
        await WorkflowService(workflow_config(failing)).execute("test-workflow", ["payload"])
