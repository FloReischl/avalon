"""Workflow runtime updates and live execution events."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.schemas import (
    WorkflowConfirmationRequest,
    WorkflowConfirmationResponse,
    WorkflowConfirmationSubmitRequest,
    WorkflowRuntimeUpdateRequest,
)
from app.api.routes.chats import get_chat_repository
from app.persistence.chat_repository import ChatRepository
from app.persistence.workflow_execution_repository import WorkflowExecutionRepository
from app.services.workflow_events import WorkflowExecutionEvent, get_workflow_event_manager
from app.workflow_confirmations import (
    ConfirmationCancelled,
    ConfirmationValidationError,
    WorkflowConfirmation,
    get_workflow_confirmation_manager,
)

router = APIRouter(prefix="/workflow-executions", tags=["workflows"])


def get_workflow_execution_repository(
    chat_repository: ChatRepository = Depends(get_chat_repository),
) -> WorkflowExecutionRepository:
    """Reuse the standard request-scoped Avalon persistence wiring."""
    return WorkflowExecutionRepository(chat_repository.session_factory)


def _confirmation_response(confirmation: WorkflowConfirmation) -> WorkflowConfirmationResponse:
    return WorkflowConfirmationResponse(
        id=confirmation.id,
        execution_id=confirmation.execution_id,
        schema=confirmation.schema,
        rows=confirmation.rows,
    )


def _owned_execution(
    execution_id: int, http_request: Request, repository: WorkflowExecutionRepository
):
    agent_id = http_request.scope.get("avalon.agent_id")
    if agent_id is None:
        raise HTTPException(status_code=401, detail="Bearer token required.")
    execution = repository.get(execution_id)
    if execution is None or not repository.chat_matches_agent(
        execution.progress_message.chat_id, agent_id
    ):
        raise HTTPException(status_code=401, detail="Workflow execution does not belong to agent.")
    return execution


def _owned_confirmation(
    confirmation_id: str, http_request: Request, repository: WorkflowExecutionRepository
) -> WorkflowConfirmation:
    confirmation = get_workflow_confirmation_manager().pending()
    if confirmation is None or confirmation.id != confirmation_id:
        raise HTTPException(status_code=404, detail="Workflow confirmation does not exist or has already been resolved.")
    _owned_execution(confirmation.execution_id, http_request, repository)
    return confirmation


@router.get("/confirmations/pending", response_model=WorkflowConfirmationResponse | None)
async def pending_confirmation(
    http_request: Request,
    repository: WorkflowExecutionRepository = Depends(get_workflow_execution_repository),
) -> WorkflowConfirmationResponse | None:
    """Expose the one pending workflow confirmation to the local UI."""
    confirmation = get_workflow_confirmation_manager().pending()
    if confirmation is None:
        return None
    _owned_execution(confirmation.execution_id, http_request, repository)
    return _confirmation_response(confirmation)


@router.post("/confirmations/{confirmation_id}/confirm", status_code=204)
async def confirm_confirmation(
    confirmation_id: str,
    request: WorkflowConfirmationSubmitRequest,
    http_request: Request,
    repository: WorkflowExecutionRepository = Depends(get_workflow_execution_repository),
) -> None:
    try:
        _owned_confirmation(confirmation_id, http_request, repository)
        get_workflow_confirmation_manager().confirm(confirmation_id, request.rows)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConfirmationValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/confirmations/{confirmation_id}/cancel", status_code=204)
async def cancel_confirmation(
    confirmation_id: str,
    http_request: Request,
    repository: WorkflowExecutionRepository = Depends(get_workflow_execution_repository),
) -> None:
    try:
        _owned_confirmation(confirmation_id, http_request, repository)
        get_workflow_confirmation_manager().cancel(confirmation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _event(event: WorkflowExecutionEvent) -> str:
    return "event: workflow_execution\ndata: " + json.dumps({"workflow_execution_id": event.id, "state": event.state, "progress_content": event.progress_content}) + "\n\n"


@router.patch("/{execution_id}/runtime")
async def update_runtime(
    execution_id: int,
    request: WorkflowRuntimeUpdateRequest,
    http_request: Request,
    repository: WorkflowExecutionRepository = Depends(get_workflow_execution_repository),
):
    _owned_execution(execution_id, http_request, repository)
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


@router.post("/{execution_id}/confirmation")
async def request_confirmation(
    execution_id: int,
    request: WorkflowConfirmationRequest,
    http_request: Request,
    repository: WorkflowExecutionRepository = Depends(get_workflow_execution_repository),
) -> list[dict[str, object]]:
    """Block one owned running workflow until its confirmation is resolved."""
    execution = _owned_execution(execution_id, http_request, repository)
    if execution.state != "running":
        raise HTTPException(status_code=409, detail="Workflow execution is not running.")
    manager = get_workflow_confirmation_manager()
    try:
        confirmation = manager.create(execution_id, request.confirmation_schema, request.rows)
    except ConfirmationValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        return await manager.wait(confirmation.id)
    except ConfirmationCancelled as exc:
        raise HTTPException(status_code=409, detail="workflow_confirmation_cancelled") from exc


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
