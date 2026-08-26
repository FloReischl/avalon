"""Text-chat endpoint contract."""

from fastapi import APIRouter, HTTPException, status

from avalo_backend.api.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def create_chat_response(request: ChatRequest) -> ChatResponse:
    """Return a complete model response once chat is implemented."""

    del request
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Text chat is not implemented yet.",
    )

