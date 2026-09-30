"""Workflow execution persistence lifecycle tests."""

from pathlib import Path

import pytest

from app.persistence.chat_repository import ChatRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.persistence.migrations import run_migrations
from app.persistence.workflow_execution_repository import WorkflowExecutionRepository


@pytest.fixture
def repository(tmp_path: Path):
    path = tmp_path / "avalon.sqlite"
    run_migrations(path)
    engine = create_database_engine(path)
    factory = create_session_factory(engine)
    try:
        chat = ChatRepository(factory).create_chat("Workflow")
        yield WorkflowExecutionRepository(factory), chat
    finally:
        engine.dispose()


def test_creates_one_empty_assistant_message_and_running_execution(repository) -> None:
    repo, chat = repository

    execution = repo.create(chat.id, "only-a-hash")

    assert execution.state == "running"
    assert execution.runtime_token_hash == "only-a-hash"
    loaded = repo.get(execution.id)
    assert loaded is not None and loaded.message.content == ""


def test_snapshot_replaces_progress_and_terminal_state_freezes_execution(repository) -> None:
    repo, chat = repository
    execution = repo.create(chat.id, "hash")

    first = repo.update(execution.id, state=None, progress_content=["one"], has_progress=True)
    second = repo.update(execution.id, state="failed", progress_content=["two"], has_progress=True)

    assert first is not None and first.progress_content == '["one"]'
    assert second is not None and second.state == "failed"
    with pytest.raises(ValueError, match="terminal"):
        repo.update(execution.id, state=None, progress_content=["three"], has_progress=True)


def test_progress_rejects_reset_to_null(repository) -> None:
    repo, chat = repository
    execution = repo.create(chat.id, "hash")

    with pytest.raises(ValueError, match="cannot be reset"):
        repo.update(execution.id, state=None, progress_content=None, has_progress=True)
