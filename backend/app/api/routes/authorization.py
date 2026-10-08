"""Browser decisions for pending authorization requests."""

from fastapi import APIRouter, HTTPException

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
