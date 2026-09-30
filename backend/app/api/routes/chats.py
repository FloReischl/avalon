"""Persistent chat-management endpoints."""

from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.schemas import (
    ChatDetailResponse,
    ChatSummaryResponse,
    ProgressMessageResponse,
    TextMessageResponse,
    RenameChatRequest,
    SetChatPinnedRequest,
    ProactivePermissionResponse,
    ProactivePermissionUpdateRequest,
)
from app.persistence.authorization_repository import AuthorizationRepository
from app.user_config import get_user_config

from app.persistence.chat_repository import ChatRepository
from app.persistence.models import ProgressMessage, TextMessage
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


def get_authorization_repository():
    engine = create_database_engine()
    repository = AuthorizationRepository(create_session_factory(engine))
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
            TextMessageResponse(
                id=message.id,
                kind="text",
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
            if isinstance(message, TextMessage)
            else ProgressMessageResponse(
                id=message.id,
                kind="progress",
                created_at=message.created_at,
                updated_at=message.updated_at,
                messages=json.loads(message.messages),
                workflow_execution={
                    "id": message.workflow_execution.id,
                    "workflow_key": message.workflow_execution.workflow_key,
                    "state": message.workflow_execution.state,
                },
            )
            for message in messages
            if isinstance(message, (TextMessage, ProgressMessage))
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


def _proactive_permissions(
    chat_id: int,
    repository: AuthorizationRepository,
    default_chat_principal_key: str = "chat-default",
) -> list[ProactivePermissionResponse]:
    principal_id = repository.get_effective_principal_id_for_chat(
        chat_id, default_chat_principal_key
    )
    if principal_id is None:
        raise HTTPException(status_code=404, detail=f"Chat {chat_id} does not exist.")
    now = datetime.now()
    result: list[ProactivePermissionResponse] = []
    for permission, catalog in repository.get_active_principal_permissions(principal_id):
        grant = repository.get_active_grant(permission.id, now)
        if permission.validity_type == "range" and grant is None:
            continue
        result.append(
            ProactivePermissionResponse(
                id=permission.id,
                context=catalog.context,
                key=catalog.key,
                validity_type=permission.validity_type,
                default_expiry=permission.default_expiry,
                grant=(
                    {"id": grant.id, "expires_at": grant.valid_to}
                    if grant is not None else None
                ),
                read_only=permission.validity_type == "range",
            )
        )
    return result


@router.get("/{chat_id}/permissions", response_model=list[ProactivePermissionResponse])
def list_proactive_permissions(
    chat_id: int,
    repository: AuthorizationRepository = Depends(get_authorization_repository),
) -> list[ProactivePermissionResponse]:
    """Show active grants/configured permissions for one chat's effective principal."""
    return _proactive_permissions(
        chat_id, repository, get_user_config().chat_default_principal_key
    )


@router.put("/{chat_id}/permissions/{permission_id}", response_model=ProactivePermissionResponse)
def save_proactive_permission(
    chat_id: int,
    permission_id: int,
    request: ProactivePermissionUpdateRequest,
    repository: AuthorizationRepository = Depends(get_authorization_repository),
) -> ProactivePermissionResponse:
    """Directly persist a proactive duration or permanent grant for this chat."""
    principal_id = repository.get_effective_principal_id_for_chat(
        chat_id, get_user_config().chat_default_principal_key
    )
    if principal_id is None:
        raise HTTPException(status_code=404, detail=f"Chat {chat_id} does not exist.")
    permission = next(
        (
            definition
            for definition, _ in repository.get_active_principal_permissions(principal_id)
            if definition.id == permission_id
        ),
        None,
    )
    if permission is None:
        raise HTTPException(status_code=404, detail="Permission does not belong to this chat.")
    if permission.validity_type == "range":
        raise HTTPException(status_code=422, detail="Range grants cannot be modified proactivity.")
    now = datetime.now()
    try:
        if request.granted:
            repository.save_proactive_grant(
                permission.id, permission.validity_type, request.expires_at, now
            )
        else:
            repository.revoke_proactive_grant(permission.id, now)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return next(
        item
        for item in _proactive_permissions(
            chat_id, repository, get_user_config().chat_default_principal_key
        )
        if item.id == permission_id
    )


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
