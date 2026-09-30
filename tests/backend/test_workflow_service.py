import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.workflows import WorkflowExecutionError, WorkflowService
from app.workflows_config import WorkflowsConfig
from app.persistence.chat_repository import ChatRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.persistence.migrations import run_migrations
from app.persistence.workflow_execution_repository import WorkflowExecutionRepository


WORKFLOW_FILE = Path(__file__).resolve().parents[1] / "data" / "test-workflow.py"
OUTPUT_FILE = Path("/tmp/avalon/test-output.txt")


def workflow_config(path: Path = WORKFLOW_FILE) -> WorkflowsConfig:
    return WorkflowsConfig.model_validate(
        {"workflows": [{"key": "test-workflow", "file_path": str(path)}]}
    )


@pytest.mark.asyncio
async def test_executes_registered_workflow_with_json_stdin(tmp_path: Path) -> None:
    OUTPUT_FILE.unlink(missing_ok=True)
    payload = {"message": "Hallo Kenny", "items": [1, True, None]}
    database = tmp_path / "avalon.sqlite"
    run_migrations(database)
    engine = create_database_engine(database)
    factory = create_session_factory(engine)
    chat_repository = ChatRepository(factory)
    chat = chat_repository.create_chat_with_message(
        "Workflow", "user", "Starte den Workflow"
    )
    avatar = SimpleNamespace(
        persona="Test Persona",
        instructions="Test Instructions",
    )
    service = WorkflowService(
        workflow_config(),
        WorkflowExecutionRepository(factory),
        chat_repository,
        avatar,
    )

    execution_id = await service.execute(
        "test-workflow", payload, chat.id, "turn-1", "http://localhost"
    )
    await asyncio.sleep(0.1)

    try:
        output = OUTPUT_FILE.read_text(encoding="utf-8")
        envelope = json.loads(output)
        assert envelope["payload"] == payload
        assert envelope["avalon"]["workflow_execution_id"] == execution_id
        assert envelope["avalon"]["backend_url"] == "http://localhost"
        assert envelope["avalon"]["runtime_token"]
        assert envelope["avalon"]["model_persona"] == "Test Persona"
        assert envelope["avalon"]["model_instructions"] == "Test Instructions"
        assert envelope["avalon"]["model_context"] == [
            {"role": "user", "content": "Starte den Workflow"}
        ]
        assert envelope["avalon"]["current_datetime"].endswith(
            "(Europe/Berlin)\nAktueller Ort: München, Deutschland"
        )
        assert WorkflowExecutionRepository(factory).get(execution_id).state == "completed"
    finally:
        engine.dispose()


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
        await WorkflowService(workflow_config()).execute(
            "unknown", {"value": 1}, 1, "turn-1", "http://localhost"
        )

    assert not started


@pytest.mark.asyncio
async def test_nonzero_workflow_exit_marks_execution_failed(tmp_path: Path) -> None:
    failing = tmp_path / "failing.py"
    failing.write_text("import sys\nsys.exit(3)\n", encoding="utf-8")

    database = tmp_path / "avalon.sqlite"
    run_migrations(database)
    engine = create_database_engine(database)
    factory = create_session_factory(engine)
    chat = ChatRepository(factory).create_chat("Workflow")
    repository = WorkflowExecutionRepository(factory)
    try:
        execution_id = await WorkflowService(
            workflow_config(failing),
            repository,
            ChatRepository(factory),
            SimpleNamespace(persona="Test Persona", instructions="Test Instructions"),
        ).execute(
            "test-workflow", ["payload"], chat.id, "turn-1", "http://localhost"
        )
        await asyncio.sleep(0.1)
        execution = repository.get(execution_id)
        assert execution is not None
        assert execution.state == "failed"
        assert execution.progress_message.messages == '["Workflow failed (exit code 3)"]'
    finally:
        engine.dispose()
