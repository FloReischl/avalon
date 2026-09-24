"""Browser decisions for pending authorization requests."""

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.schemas import AuthorizationDecisionRequest, PendingAuthorizationRequestResponse
from app.authorization.runtime import get_authorization_request_manager


router = APIRouter(prefix="/authorization-requests", tags=["authorization"])


@router.get("", response_model=list[PendingAuthorizationRequestResponse])
async def list_pending_authorization_requests() -> list[PendingAuthorizationRequestResponse]:
    """List all pending requests for the global permission inbox."""
    return [
        PendingAuthorizationRequestResponse(
            id=request.id, context=request.context, key=request.key,
            items=request.formatted_items, validity_type=request.validity_type,
            default_expiry=request.default_expiry, source_label=request.source_label,
        )
        for request in get_authorization_request_manager().pending_requests()
    ]


@router.get("/events")
async def authorization_events() -> StreamingResponse:
    """Emit compact invalidations whenever the pending request list changes."""
    manager = get_authorization_request_manager()
    queue = manager.subscribe()

    async def events() -> AsyncIterator[str]:
        try:
            yield f"event: authorization_requests_changed\ndata: {json.dumps({})}\n\n"
            while True:
                await queue.get()
                yield f"event: authorization_requests_changed\ndata: {json.dumps({})}\n\n"
        finally:
            manager.unsubscribe(queue)

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/{request_id}/confirm", status_code=204)
async def confirm_authorization(
    request_id: str, request: AuthorizationDecisionRequest
) -> None:
    """Resume one pending request with the selected original items."""
    try:
        get_authorization_request_manager().confirm(
            request_id, request.approved_item_indexes, request.duration_seconds
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=404 if isinstance(exc, KeyError) else 422, detail=str(exc)) from exc


@router.post("/{request_id}/abort", status_code=204)
async def abort_authorization(request_id: str) -> None:
    """Abort the waiting agent operation."""
    try:
        get_authorization_request_manager().abort(request_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
