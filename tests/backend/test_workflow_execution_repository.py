"""Workflow execution persistence lifecycle tests."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.persistence.chat_repository import ChatRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.persistence.migrations import run_migrations
from app.persistence.workflow_execution_repository import WorkflowExecutionRepository
from app.services.workflows import WorkflowService


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


def test_creates_one_progress_message_and_running_execution(repository) -> None:
    repo, chat = repository

    execution = repo.create(chat.id, "invocation-1", "morning-news")

    assert execution.state == "running"
    loaded = repo.get(execution.id)
    assert loaded is not None
    assert loaded.workflow_key == "morning-news"
    assert loaded.progress_message.invocation_id == "invocation-1"
    assert loaded.progress_message.messages == "[]"


def test_progress_message_is_positioned_once_per_invocation(repository) -> None:
    repo, chat = repository

    first = repo.create(chat.id, "turn-1", "morning-news")
    second = repo.create(chat.id, "turn-2", "morning-news")

    assert first.progress_message.id != second.progress_message.id
    assert first.progress_message.seq < second.progress_message.seq


def test_same_chat_invocation_cannot_create_a_second_progress_message(repository) -> None:
    repo, chat = repository
    repo.create(chat.id, "turn-1", "morning-news")

    with pytest.raises(Exception):
        repo.create(chat.id, "turn-1", "morning-news")


def test_snapshot_replaces_progress_and_terminal_state_freezes_execution(repository) -> None:
    repo, chat = repository
    execution = repo.create(chat.id, "invocation-1", "morning-news")

    first = repo.update(execution.id, state=None, progress_content=["one"], has_progress=True)
    second = repo.update(execution.id, state="failed", progress_content=["two"], has_progress=True)

    assert first is not None and first.progress_message.messages == '["one"]'
    assert second is not None and second.state == "failed"
    with pytest.raises(ValueError, match="terminal"):
        repo.update(execution.id, state=None, progress_content=["three"], has_progress=True)


def test_progress_rejects_reset_to_null(repository) -> None:
    repo, chat = repository
    execution = repo.create(chat.id, "invocation-1", "morning-news")

    with pytest.raises(ValueError, match="cannot be reset"):
        repo.update(execution.id, state=None, progress_content=None, has_progress=True)


def test_process_failure_appends_to_existing_progress(repository) -> None:
    repo, chat = repository
    execution = repo.create(chat.id, "invocation-1", "morning-news")
    repo.update(execution.id, state=None, progress_content=["Podcast 1 fertig"], has_progress=True)

    failed = repo.append_process_failure(execution.id, "Workflow failed to start: permission denied")

    assert failed is not None
    assert failed.state == "failed"
    assert failed.progress_message.messages == (
        '["Podcast 1 fertig", "Workflow failed to start: permission denied"]'
    )


@pytest.mark.asyncio
async def test_start_failure_appends_clear_system_progress(monkeypatch, repository) -> None:
    repo, chat = repository

    class Config:
        @staticmethod
        def get(_key):
            return type("Workflow", (), {"file_path": Path("/workflow.py")})()

    async def fail_to_start(*_args, **_kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr("app.services.workflows.asyncio.create_subprocess_exec", fail_to_start)
    monkeypatch.setattr(
        "app.services.workflows.get_avalon_state",
        lambda: SimpleNamespace(
            current_avatar=SimpleNamespace(persona="Test", instructions="Test")
        ),
    )
    service = WorkflowService(Config(), repo, ChatRepository(repo._session_factory))
    monkeypatch.setattr(service, "_publish", lambda _execution: None)

    with pytest.raises(OSError, match="permission denied"):
        await service.execute(
            "podcast", {}, chat.id, "invocation-1", "http://localhost", chat.principal_id
        )

    execution = repo.get(1)
    assert execution is not None
    assert execution.state == "failed"
    assert execution.progress_message.messages == '["Workflow failed to start: permission denied"]'
