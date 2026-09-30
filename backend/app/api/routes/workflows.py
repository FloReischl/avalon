"""Workflow runtime updates and live execution events."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.schemas import WorkflowRuntimeUpdateRequest
from app.persistence.database import create_database_engine, create_session_factory
from app.persistence.workflow_execution_repository import WorkflowExecutionRepository
from app.services.workflow_events import WorkflowExecutionEvent, get_workflow_event_manager

router = APIRouter(prefix="/workflow-executions", tags=["workflows"])


def _repository() -> tuple[WorkflowExecutionRepository, object]:
    engine = create_database_engine()
    return WorkflowExecutionRepository(create_session_factory(engine)), engine


def _event(event: WorkflowExecutionEvent) -> str:
    return "event: workflow_execution\ndata: " + json.dumps({"workflow_execution_id": event.id, "state": event.state, "progress_content": event.progress_content}) + "\n\n"


@router.patch("/{execution_id}/runtime")
def update_runtime(execution_id: int, request: WorkflowRuntimeUpdateRequest, authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Workflow runtime token required.")
    token = authorization.removeprefix("Bearer ")
    repository, engine = _repository()
    try:
        execution = repository.get(execution_id)
        if execution is None or not secrets_compare(execution.runtime_token_hash, hashlib.sha256(token.encode()).hexdigest()):
            raise HTTPException(status_code=401, detail="Invalid workflow runtime token.")
        provided = "progress_content" in request.model_fields_set
        if provided and (request.progress_content is None or not request.progress_content or not all(isinstance(item, str) and item for item in request.progress_content)):
            raise HTTPException(status_code=422, detail="progress_content must be a non-empty list of strings.")
        try:
            updated = repository.update(execution_id, state=request.state, progress_content=request.progress_content, has_progress=provided)
        except (LookupError, ValueError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if updated is not None:
            get_workflow_event_manager().publish(WorkflowExecutionEvent(updated.id, updated.state, json.loads(updated.progress_content) if updated.progress_content else None))
        return {"changed": updated is not None}
    finally:
        engine.dispose()


def secrets_compare(left: str, right: str) -> bool:
    import hmac
    return hmac.compare_digest(left, right)


@router.get("/events")
async def events(request: Request) -> StreamingResponse:
    queue = get_workflow_event_manager().subscribe()
    async def stream() -> AsyncIterator[str]:
        try:
            while True:
                if await request.is_disconnected():
                    return
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield _event(event)
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            get_workflow_event_manager().unsubscribe(queue)
    return StreamingResponse(stream(), media_type="text/event-stream")
