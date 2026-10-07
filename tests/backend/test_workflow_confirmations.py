"""Focused contracts for in-memory workflow confirmations."""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routes import workflows
from app.api.schemas import WorkflowConfirmationRequest, WorkflowConfirmationSubmitRequest
from app.persistence.chat_repository import ChatRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.persistence.migrations import run_migrations
from app.persistence.models import Agent
from app.persistence.workflow_execution_repository import WorkflowExecutionRepository
from app.workflow_confirmations import (
    ConfirmationCancelled,
    ConfirmationValidationError,
    WorkflowConfirmationManager,
)


SCHEMA = {
    "title": "Review",
    "columns": [
        {"key": "id", "type": "str", "nullable": False, "editable": False, "visible": False},
        {"key": "title", "type": "str", "nullable": False, "editable": True, "visible": True},
    ],
}
ROWS = [{"id": "4711", "title": "Original"}]


def request_for(agent_id: int) -> SimpleNamespace:
    return SimpleNamespace(scope={"avalon.agent_id": agent_id})


def test_valid_confirmation_blocks_and_returns_all_edited_rows() -> None:
    manager = WorkflowConfirmationManager()

    async def scenario() -> None:
        confirmation = manager.create(7, SCHEMA, ROWS)
        assert confirmation.rows == [{"id": "4711", "title": "Original", "avalon_confirmation": "unconfirmed"}]
        waiting = asyncio.create_task(manager.wait(confirmation.id))
        await asyncio.sleep(0)
        manager.confirm(confirmation.id, [{"id": "4711", "title": "Edited", "avalon_confirmation": "approved"}])
        assert await waiting == [{"id": "4711", "title": "Edited", "avalon_confirmation": "approved"}]

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "rows",
    [
        [{"id": "changed", "title": "Original", "avalon_confirmation": "approved"}],
        [],
        [{"id": "4711", "title": "Original", "avalon_confirmation": "unconfirmed"}],
    ],
)
def test_submit_rejects_readonly_changes_row_count_changes_and_unconfirmed(rows) -> None:
    manager = WorkflowConfirmationManager()
    async def scenario() -> None:
        confirmation = manager.create(7, SCHEMA, ROWS)
        with pytest.raises(ConfirmationValidationError):
            manager.confirm(confirmation.id, rows)
        manager.cancel(confirmation.id)
        with pytest.raises(ConfirmationCancelled):
            await manager.wait(confirmation.id)
    asyncio.run(scenario())


def test_cancel_unblocks_with_identifiable_exception() -> None:
    manager = WorkflowConfirmationManager()

    async def scenario() -> None:
        confirmation = manager.create(7, SCHEMA, ROWS)
        waiting = asyncio.create_task(manager.wait(confirmation.id))
        await asyncio.sleep(0)
        manager.cancel(confirmation.id)
        with pytest.raises(ConfirmationCancelled):
            await waiting

    asyncio.run(scenario())


def test_float_column_accepts_json_integer_but_not_boolean() -> None:
    manager = WorkflowConfirmationManager()
    schema = {
        "title": "Number",
        "columns": [{"key": "value", "type": "float", "nullable": False, "editable": True, "visible": True}],
    }

    async def scenario() -> None:
        confirmation = manager.create(7, schema, [{"value": 42}])
        manager.cancel(confirmation.id)
        with pytest.raises(ConfirmationCancelled):
            await manager.wait(confirmation.id)
        with pytest.raises(ConfirmationValidationError):
            manager.create(7, schema, [{"value": True}])

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "schema,rows",
    [
        ({"title": "", "columns": []}, ROWS),
        (SCHEMA, [{"id": "4711", "title": 1}]),
        (SCHEMA, [{"id": "4711", "title": "Original", "avalon_confirmation": "approved"}]),
    ],
)
def test_invalid_input_does_not_create_pending_confirmation(schema, rows) -> None:
    manager = WorkflowConfirmationManager()
    with pytest.raises(ConfirmationValidationError):
        manager.create(7, schema, rows)
    assert manager.pending() is None


def test_runtime_confirmation_keeps_execution_running_and_returns_rows(monkeypatch, tmp_path) -> None:
    database = tmp_path / "avalon.sqlite"
    run_migrations(database)
    engine = create_database_engine(database)
    factory = create_session_factory(engine)
    repository = WorkflowExecutionRepository(factory)
    with factory.begin() as session:
        agent = Agent(key="workflow-test", name="Workflow test")
        session.add(agent)
        session.flush()
        agent_id = agent.id
    chat = ChatRepository(factory).create_chat("Workflow", agent_id=agent_id)
    execution = repository.create(chat.id, "turn-1", "review")
    manager = WorkflowConfirmationManager()
    monkeypatch.setattr(workflows, "get_workflow_confirmation_manager", lambda: manager)

    async def scenario() -> None:
        waiting = asyncio.create_task(
            workflows.request_confirmation(
                execution.id,
                WorkflowConfirmationRequest.model_validate({"schema": SCHEMA, "rows": ROWS}),
                request_for(chat.agent_id),
                repository,
            )
        )
        await asyncio.sleep(0)
        pending = manager.pending()
        assert pending is not None
        await workflows.confirm_confirmation(
            pending.id,
            WorkflowConfirmationSubmitRequest(rows=[{"id": "4711", "title": "Edited", "avalon_confirmation": "rejected"}]),
        )
        assert await waiting == [{"id": "4711", "title": "Edited", "avalon_confirmation": "rejected"}]

    try:
        asyncio.run(scenario())
        assert repository.get(execution.id).state == "running"
    finally:
        engine.dispose()


def test_runtime_invalid_request_is_400_and_creates_nothing(monkeypatch, tmp_path) -> None:
    database = tmp_path / "avalon.sqlite"
    run_migrations(database)
    engine = create_database_engine(database)
    factory = create_session_factory(engine)
    repository = WorkflowExecutionRepository(factory)
    with factory.begin() as session:
        agent = Agent(key="workflow-test", name="Workflow test")
        session.add(agent)
        session.flush()
        agent_id = agent.id
    chat = ChatRepository(factory).create_chat("Workflow", agent_id=agent_id)
    execution = repository.create(chat.id, "turn-1", "review")
    manager = WorkflowConfirmationManager()
    monkeypatch.setattr(workflows, "get_workflow_confirmation_manager", lambda: manager)

    async def scenario() -> None:
        with pytest.raises(HTTPException) as error:
            await workflows.request_confirmation(
                execution.id,
                WorkflowConfirmationRequest.model_validate({"schema": SCHEMA, "rows": [{"id": "4711", "title": 3}]}),
                request_for(chat.agent_id),
                repository,
            )
        assert error.value.status_code == 400

    try:
        asyncio.run(scenario())
        assert manager.pending() is None
    finally:
        engine.dispose()


def test_local_ui_confirmation_routes_are_agent_independent(monkeypatch, tmp_path) -> None:
    database = tmp_path / "avalon.sqlite"
    run_migrations(database)
    engine = create_database_engine(database)
    factory = create_session_factory(engine)
    repository = WorkflowExecutionRepository(factory)
    with factory.begin() as session:
        owner = Agent(key="owner", name="Owner")
        other = Agent(key="other", name="Other")
        session.add_all([owner, other])
        session.flush()
        owner_id, other_id = owner.id, other.id
    chat = ChatRepository(factory).create_chat("Workflow", agent_id=owner_id)
    execution = repository.create(chat.id, "turn-1", "review")
    manager = WorkflowConfirmationManager()
    monkeypatch.setattr(workflows, "get_workflow_confirmation_manager", lambda: manager)

    async def scenario() -> None:
        waiting = asyncio.create_task(
            workflows.request_confirmation(
                execution.id, WorkflowConfirmationRequest.model_validate({"schema": SCHEMA, "rows": ROWS}),
                request_for(owner_id), repository,
            )
        )
        await asyncio.sleep(0)
        pending = manager.pending()
        assert pending is not None
        assert (await workflows.pending_confirmation()).id == pending.id
        await workflows.cancel_confirmation(pending.id)
        with pytest.raises(HTTPException) as error:
            await waiting
        assert error.value.detail == "workflow_confirmation_cancelled"

    try:
        asyncio.run(scenario())
    finally:
        engine.dispose()
