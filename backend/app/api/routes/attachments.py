"""Attachment upload and download endpoints."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.schemas import AttachmentResponse
from app.persistence.attachment_repository import AttachmentRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.services.attachments import AttachmentService, AttachmentTooLargeError


router = APIRouter(tags=["attachments"])


def get_attachment_service():
    """Create one attachment service for a request."""
    engine = create_database_engine()
    service = AttachmentService(AttachmentRepository(create_session_factory(engine)))
    try:
        yield service
    finally:
        engine.dispose()


def _response(attachment) -> AttachmentResponse:
    return AttachmentResponse(
        id=attachment.id,
        original_file_name=attachment.original_file_name,
        mime_type=attachment.mime_type,
        size=attachment.size,
        created_at=attachment.created_at,
    )


@router.post(
    "/messages/{message_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    message_id: int,
    file: UploadFile = File(...),
    service: AttachmentService = Depends(get_attachment_service),
) -> AttachmentResponse:
    """Create one file attachment and directly link it to a message."""
    try:
        attachment = await service.upload_for_message(message_id, file)
    except AttachmentTooLargeError as exc:
        raise HTTPException(status_code=413, detail="Attachment exceeds 50 MB.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        await file.close()

    if attachment is None:
        raise HTTPException(status_code=404, detail=f"Message {message_id} does not exist.")
    return _response(attachment)


@router.get("/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    service: AttachmentService = Depends(get_attachment_service),
) -> FileResponse:
    """Download one immutable Avalon attachment."""
    attachment = service.get(attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail=f"Attachment {attachment_id} does not exist.")
    path = service.path_for(attachment)
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Attachment file {attachment_id} does not exist.")
    return FileResponse(
        path,
        media_type=attachment.mime_type,
        filename=attachment.original_file_name,
    )
