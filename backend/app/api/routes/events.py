"""The shared server-sent-event endpoint for Avalon invalidations."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.authorization.runtime import get_authorization_request_manager
from app.services.notification_hub import NotificationHub
from app.services.workflow_events import get_workflow_event_manager
from app.workflow_confirmations import get_workflow_confirmation_manager


router = APIRouter(tags=["events"])


@router.get("/events")
async def events() -> StreamingResponse:
    """Expose all existing local invalidations through one SSE connection."""
    hub = NotificationHub(
        get_authorization_request_manager(),
        get_workflow_confirmation_manager(),
        get_workflow_event_manager(),
    )
    return StreamingResponse(hub.events(), media_type="text/event-stream")
