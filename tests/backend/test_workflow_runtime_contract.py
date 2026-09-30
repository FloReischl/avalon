"""Contract tests for persisted workflow runtime updates."""

import asyncio
import hashlib

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routes.workflows import get_workflow_execution_repository, router
from app.persistence.chat_repository import ChatRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.persistence.migrations import run_migrations
from app.persistence.workflow_execution_repository import WorkflowExecutionRepository
from app.services.workflow_events import get_workflow_event_manager


def test_runtime_token_updates_progress_and_publishes_only_real_change(tmp_path) -> None:
    database = tmp_path / "avalon.sqlite"
    run_migrations(database)
    engine = create_database_engine(database)
    factory = create_session_factory(engine)
    repository = WorkflowExecutionRepository(factory)
    chat = ChatRepository(factory).create_chat("Workflow")
    token = "runtime-token"
    execution = repository.create(
        chat.id, "turn-1", "morning-news", hashlib.sha256(token.encode()).hexdigest()
    )
    application = FastAPI()
    application.include_router(router, prefix="/api/v1")
    application.dependency_overrides[get_workflow_execution_repository] = lambda: repository
    events = get_workflow_event_manager()
    queue = events.subscribe()

    async def request(payload: dict, bearer: str) -> int:
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                f"/api/v1/workflow-executions/{execution.id}/runtime",
                json=payload,
                headers={"Authorization": f"Bearer {bearer}"},
            )
            return response.status_code

    try:
        assert asyncio.run(request({"progress_content": ["Quelle geladen"]}, token)) == 200
        event = queue.get_nowait()
        assert event.id == execution.id
        assert event.progress_content == ["Quelle geladen"]
        assert asyncio.run(request({"progress_content": ["Quelle geladen"]}, token)) == 200
        assert queue.empty()
        assert asyncio.run(request({"state": "completed"}, "wrong")) == 401
        assert repository.get(execution.id).progress_message.messages == '["Quelle geladen"]'
    finally:
        events.unsubscribe(queue)
        engine.dispose()
