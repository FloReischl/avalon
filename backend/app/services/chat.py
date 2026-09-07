"""Text-chat application service."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime

from app.persistence.chat_repository import ChatRepository
from app.runtime.base import ModelRuntime


class ChatNotFoundError(Exception):
    """Raised when a requested persistent chat does not exist."""


@dataclass(frozen=True, slots=True)
class ChatTurn:
    """Prepared persistent chat turn ready for model generation."""

    chat_id: int
    messages: list[dict[str, str]]


class ChatService:
    """Coordinate persistent text-chat turns and model generation."""

    def __init__(
        self,
        runtime: ModelRuntime,
        repository: ChatRepository,
    ) -> None:
        self._runtime = runtime
        self._repository = repository

    def start_turn(
        self,
        chat_id: int | None,
        message: str,
    ) -> ChatTurn:
        """Persist the user input and prepare bounded model context."""
        if chat_id is None:
            title = datetime.now().strftime("New %Y-%m-%d %H:%M:%S")
            chat = self._repository.create_chat_with_message(
                title,
                "user",
                message,
            )
            chat_id = chat.id
        else:
            if self._repository.get_chat(chat_id) is None:
                raise ChatNotFoundError(f"Chat {chat_id} does not exist.")

            self._repository.add_message(chat_id, "user", message)

        context = self._repository.get_context_messages(chat_id, limit=100)
        messages = [
            {
                "role": persisted.role,
                "content": persisted.content,
            }
            for persisted in context
        ]
        return ChatTurn(chat_id=chat_id, messages=messages)

    async def stream_response(
        self,
        turn: ChatTurn,
    ) -> AsyncIterator[str]:
        """Stream a response and persist it only after successful completion."""
        response_chunks: list[str] = []

        async for chunk in self._runtime.generate_text_stream(turn.messages):
            response_chunks.append(chunk)
            yield chunk

        response = "".join(response_chunks)
        if response:
            self._repository.add_message(
                turn.chat_id,
                "assistant",
                response,
            )
