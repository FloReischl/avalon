"""Workflow runtime updates and live execution events."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.schemas import WorkflowRuntimeUpdateRequest
from app.api.routes.chats import get_chat_repository
from app.persistence.chat_repository import ChatRepository
from app.persistence.workflow_execution_repository import WorkflowExecutionRepository
from app.services.workflow_events import WorkflowExecutionEvent, get_workflow_event_manager

router = APIRouter(prefix="/workflow-executions", tags=["workflows"])


def get_workflow_execution_repository(
    chat_repository: ChatRepository = Depends(get_chat_repository),
) -> WorkflowExecutionRepository:
    """Reuse the standard request-scoped Avalon persistence wiring."""
    return WorkflowExecutionRepository(chat_repository.session_factory)


def _event(event: WorkflowExecutionEvent) -> str:
    return "event: workflow_execution\ndata: " + json.dumps({"workflow_execution_id": event.id, "state": event.state, "progress_content": event.progress_content}) + "\n\n"


@router.patch("/{execution_id}/runtime")
async def update_runtime(
    execution_id: int,
    request: WorkflowRuntimeUpdateRequest,
    http_request: Request,
    repository: WorkflowExecutionRepository = Depends(get_workflow_execution_repository),
):
    principal_id = http_request.scope.get("avalon.principal_id")
    if principal_id is None:
        raise HTTPException(status_code=401, detail="Bearer token required.")
    execution = repository.get(execution_id)
    if execution is None or not repository.chat_matches_principal(
        execution.progress_message.chat_id, principal_id
    ):
        raise HTTPException(status_code=401, detail="Workflow execution does not belong to principal.")
    provided = "progress_content" in request.model_fields_set
    if provided and (request.progress_content is None or not request.progress_content or not all(isinstance(item, str) and item for item in request.progress_content)):
        raise HTTPException(status_code=422, detail="progress_content must be a non-empty list of strings.")
    try:
        updated = repository.update(execution_id, state=request.state, progress_content=request.progress_content, has_progress=provided)
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if updated is not None:
        get_workflow_event_manager().publish(
            WorkflowExecutionEvent(
                updated.id,
                updated.state,
                json.loads(updated.progress_message.messages),
            )
        )
    return {"changed": updated is not None}
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
