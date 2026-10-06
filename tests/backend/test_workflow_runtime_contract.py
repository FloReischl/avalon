"""Contract tests for persisted workflow runtime updates."""

import asyncio
from types import SimpleNamespace

from fastapi import HTTPException

from app.api.routes.workflows import update_runtime
from app.api.schemas import WorkflowRuntimeUpdateRequest
from app.persistence.chat_repository import ChatRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.persistence.migrations import run_migrations
from app.persistence.workflow_execution_repository import WorkflowExecutionRepository
from app.services.workflow_events import get_workflow_event_manager


def test_agent_updates_own_workflow_progress_and_publishes_only_real_change(tmp_path) -> None:
    database = tmp_path / "avalon.sqlite"
    run_migrations(database)
    engine = create_database_engine(database)
    factory = create_session_factory(engine)
    repository = WorkflowExecutionRepository(factory)
    chat = ChatRepository(factory).create_chat("Workflow")
    execution = repository.create(chat.id, "turn-1", "morning-news")
    events = get_workflow_event_manager()
    queue = events.subscribe()

    async def request(payload: dict, agent_id: int | None) -> int:
        try:
            await update_runtime(
                execution.id,
                WorkflowRuntimeUpdateRequest.model_validate(payload),
                SimpleNamespace(scope={"avalon.agent_id": agent_id}),
                repository,
            )
        except HTTPException as exc:
            return exc.status_code
        return 200

    try:
        async def scenario() -> None:
            assert await request({"progress_content": ["Quelle geladen"]}, chat.agent_id) == 200
            event = queue.get_nowait()
            assert event.id == execution.id
            assert event.progress_content == ["Quelle geladen"]
            assert await request({"progress_content": ["Quelle geladen"]}, chat.agent_id) == 200
            assert queue.empty()
            assert await request({"state": "completed"}, 999) == 401

        asyncio.run(scenario())
        assert repository.get(execution.id).progress_message.messages == '["Quelle geladen"]'
    finally:
        events.unsubscribe(queue)
        engine.dispose()
