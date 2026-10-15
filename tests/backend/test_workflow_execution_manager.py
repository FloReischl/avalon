"""Tests for the local workflow execution debug helper."""

from pathlib import Path
import sys

import pytest
from sqlalchemy import func, select

sys.path.insert(0, str(Path(__file__).parents[2] / "workflows"))

import avalon_workflows.execution_manager as manager_module
from app.persistence.database import create_database_engine, create_session_factory
from app.persistence.migrations import run_migrations
from app.persistence.models import Agent, Chat, ProgressMessage, WorkflowExecution
from avalon_workflows.execution_manager import WorkflowExecutionManager


@pytest.fixture
def local_execution_manager(monkeypatch, tmp_path: Path):
    database_path = tmp_path / "avalon.sqlite"
    run_migrations(database_path)
    engine = create_database_engine(database_path)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        podcast = Agent(key="podcast", name="Hedwig", icon="🦉")
        session.add(podcast)
        session.flush()
        default = session.scalar(select(Agent).where(Agent.key == "default"))
        assert default is not None
        session.add_all(
            [
                Chat(title="Debug chat", agent_id=podcast.id),
                Chat(title="Debug chat", agent_id=podcast.id),
                Chat(title="Other agent chat", agent_id=default.id),
            ]
        )

    monkeypatch.setattr(
        manager_module,
        "WORKFLOWS_CONFIG_PATH",
        Path("data/blueprints/user.avalon/workflows.yaml"),
    )
    monkeypatch.setattr(
        manager_module,
        "AGENTS_CONFIG_PATH",
        Path("data/blueprints/user.avalon/agents.yaml"),
    )
    monkeypatch.setattr(manager_module, "create_database_engine", lambda: engine)
    try:
        yield WorkflowExecutionManager(), factory
    finally:
        engine.dispose()


def test_creates_persistent_execution_for_latest_matching_chat(
    local_execution_manager,
) -> None:
    manager, factory = local_execution_manager

    execution_id = manager.create_execution(
        "Debug chat", "create-podcast-list", "Hedwig", "invocation-1"
    )

    with factory() as session:
        execution = session.get(WorkflowExecution, execution_id)
        assert execution is not None
        assert execution.workflow_key == "create-podcast-list"
        assert execution.state == "running"
        assert execution.progress_message.invocation_id == "invocation-1"
        assert execution.progress_message.chat_id == 2
        assert session.scalar(select(func.count()).select_from(ProgressMessage)) == 1
        assert session.scalar(select(func.count()).select_from(WorkflowExecution)) == 1


@pytest.mark.parametrize(
    ("kwargs", "exception", "message"),
    [
        (
            {"workflow_key": "missing"},
            KeyError,
            "Unknown workflow: missing",
        ),
        (
            {"agent_name": "Missing Agent"},
            KeyError,
            "Agent 'Missing Agent' not found.",
        ),
        (
            {"chat_title": "Missing chat"},
            LookupError,
            "Chat 'Missing chat' not found.",
        ),
        (
            {"chat_title": "Other agent chat"},
            ValueError,
            "Chat does not belong to agent.",
        ),
    ],
)
def test_rejects_invalid_debug_context_without_partial_records(
    local_execution_manager, kwargs, exception, message
) -> None:
    manager, factory = local_execution_manager
    arguments = {
        "chat_title": "Debug chat",
        "workflow_key": "create-podcast-list",
        "agent_name": "Hedwig",
        "invocation_id": "invocation-1",
    }
    arguments.update(kwargs)

    with pytest.raises(exception, match=message):
        manager.create_execution(**arguments)

    with factory() as session:
        assert session.scalar(select(func.count()).select_from(ProgressMessage)) == 0
        assert session.scalar(select(func.count()).select_from(WorkflowExecution)) == 0


def test_rejects_configured_agent_missing_from_database(
    local_execution_manager,
) -> None:
    manager, factory = local_execution_manager
    with factory.begin() as session:
        session.query(Chat).delete()
        session.query(Agent).where(Agent.key == "podcast").delete()

    with pytest.raises(LookupError, match="Agent 'Hedwig' is not persisted."):
        manager.create_execution(
            "Debug chat", "create-podcast-list", "Hedwig", "invocation-1"
        )

    with factory() as session:
        assert session.scalar(select(func.count()).select_from(ProgressMessage)) == 0
        assert session.scalar(select(func.count()).select_from(WorkflowExecution)) == 0
