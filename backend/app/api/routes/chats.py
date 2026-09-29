"""Persistent chat-management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.schemas import (
    ChatDetailResponse,
    ChatSummaryResponse,
    PersistentMessageResponse,
    RenameChatRequest,
    SetChatPinnedRequest,
)

from app.persistence.chat_repository import ChatRepository
from app.persistence.database import (
    create_database_engine,
    create_session_factory,
)

router = APIRouter(prefix="/chats", tags=["chats"])


def get_chat_repository():
    """Create one persistent chat repository for the request."""
    engine = create_database_engine()
    repository = ChatRepository(create_session_factory(engine))

    try:
        yield repository
    finally:
        engine.dispose()


def _summary_response(chat) -> ChatSummaryResponse:
    """Translate one persistent chat into its public summary schema."""
    return ChatSummaryResponse(
        id=chat.id,
        title=chat.title,
        pinned=chat.pinned,
        created_at=chat.created_at,
    )



@router.get("", response_model=list[ChatSummaryResponse])
def list_chats(
    repository: ChatRepository = Depends(get_chat_repository),
) -> list[ChatSummaryResponse]:
    """Return all persistent chats ordered by recent activity."""
    return [
        _summary_response(chat)
        for chat in repository.list_chats()
    ]


@router.get("/{chat_id}", response_model=ChatDetailResponse)
def get_chat(
    chat_id: int,
    repository: ChatRepository = Depends(get_chat_repository),
) -> ChatDetailResponse:
    """Return one persistent chat with its complete message history."""
    chat = repository.get_chat(chat_id)
    if chat is None:
        raise HTTPException(
            status_code=404,
            detail=f"Chat {chat_id} does not exist.",
        )

    messages = repository.get_messages(chat_id)
    attachments_by_message = repository.get_attachments_for_messages(
        [message.id for message in messages]
    )

    return ChatDetailResponse(
        id=chat.id,
        title=chat.title,
        pinned=chat.pinned,
        created_at=chat.created_at,
        compression_error_code=chat.compression_error_code,

        messages=[
            PersistentMessageResponse(
                id=message.id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
                attachments=[
                    {
                        "id": attachment.id,
                        "original_file_name": attachment.original_file_name,
                        "mime_type": attachment.mime_type,
                        "size": attachment.size,
                        "created_at": attachment.created_at,
                    }
                    for attachment in attachments_by_message.get(message.id, [])
                ],
            )
            for message in messages
        ],
    )


@router.patch("/{chat_id}", response_model=ChatSummaryResponse)
def rename_chat(
    chat_id: int,
    request: RenameChatRequest,
    repository: ChatRepository = Depends(get_chat_repository),
) -> ChatSummaryResponse:
    """Rename one persistent chat manually."""
    try:
        chat = repository.rename_chat(chat_id, request.title)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    if chat is None:
        raise HTTPException(
            status_code=404,
            detail=f"Chat {chat_id} does not exist.",
        )

    return _summary_response(chat)


@router.patch("/{chat_id}/pinned", response_model=ChatSummaryResponse)
def set_chat_pinned(
    chat_id: int,
    request: SetChatPinnedRequest,
    repository: ChatRepository = Depends(get_chat_repository),
) -> ChatSummaryResponse:
    """Persist the pinned state of one chat."""
    chat = repository.set_pinned(chat_id, request.pinned)
    if chat is None:
        raise HTTPException(
            status_code=404,
            detail=f"Chat {chat_id} does not exist.",
        )

    return _summary_response(chat)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(

    chat_id: int,
    repository: ChatRepository = Depends(get_chat_repository),
) -> Response:
    """Physically delete one persistent chat and its messages."""
    if not repository.delete_chat(chat_id):
        raise HTTPException(
            status_code=404,
            detail=f"Chat {chat_id} does not exist.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
