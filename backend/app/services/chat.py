"""Text-chat application service."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime

from app.commands import CommandRegistry, CommandRequest, parse_command
from app.persistence.chat_repository import ChatRepository
from app.user_config import AvatarConfig
from app.runtime.base import ModelRuntime


class ChatNotFoundError(Exception):
    """Raised when a requested persistent chat does not exist."""


@dataclass(frozen=True, slots=True)
class ChatTurn:
    """Prepared persistent chat turn ready for response generation."""

    chat_id: int
    messages: list[dict[str, str]]
    command_response: str | None = None
    command_request: CommandRequest | None = None


class ChatService:
    """Coordinate persistent text-chat turns and model generation."""

    def __init__(
        self,
        runtime: ModelRuntime,
        repository: ChatRepository,
        avatar: AvatarConfig | None = None,
        command_registry: CommandRegistry | None = None,
    ) -> None:
        self._runtime = runtime
        self._repository = repository
        self._avatar = avatar
        self._command_registry = command_registry or CommandRegistry()

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

        command_request = parse_command(message)
        if command_request is not None:
            return ChatTurn(
                chat_id=chat_id,
                messages=[],
                command_request=command_request,
            )

        context = self._repository.get_context_messages(chat_id, limit=100)
        messages = [
            {
                "role": persisted.role,
                "content": persisted.content,
            }
            for persisted in context
        ]
        if self._avatar is not None:
            messages.insert(
                0,
                {
                    "role": "system",
                    "content": (
                        f"{self._avatar.persona}\n\n"
                        f"{self._avatar.instructions}"
                    ),
                },
            )
        return ChatTurn(chat_id=chat_id, messages=messages)

    async def stream_response(
        self,
        turn: ChatTurn,
    ) -> AsyncIterator[str]:
        """Stream a response and persist it only after successful completion."""
        if turn.command_response is not None:
            yield turn.command_response
            self._repository.add_message(
                turn.chat_id,
                "assistant",
                turn.command_response,
            )
            return

        if turn.command_request is not None:
            command_response = await self._command_registry.execute(
                turn.command_request
            )
            yield command_response
            self._repository.add_message(
                turn.chat_id,
                "assistant",
                command_response,
            )
            return

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

    async def finalize_turn(self, turn: ChatTurn) -> None:
        """Run optional post-response work after the client receives done."""
        if (
            turn.command_response is not None
            or turn.command_request is not None
        ):
            return

        try:
            await self._try_auto_title(turn.chat_id)
        except Exception:
            # Optional post-response work must never affect a completed turn.
            return

    async def _try_auto_title(self, chat_id: int) -> None:
        """Attempt automatic title generation after roundtrip two."""
        messages = self._repository.get_messages(chat_id)

        if len(messages) != 4:
            return

        if [message.role for message in messages] != [
            "user",
            "assistant",
            "user",
            "assistant",
        ]:
            return

        if not self._repository.claim_auto_title_attempt(chat_id):
            return

        title_context = "\n".join(
            f"{message.role}: {message.content}"
            for message in messages
        )
        title_prompt = [
            {
                "role": "user",
                "content": (
                    "Erzeuge einen kurzen, prägnanten Titel für den "
                    "folgenden Chat. Antworte ausschließlich mit dem Titel, "
                    "ohne Anführungszeichen, Präfix oder Erklärung. "
                    "Maximal 200 Zeichen.\n\n"
                    f"{title_context}"
                ),
            }
        ]

        try:
            chunks = [
                chunk
                async for chunk in self._runtime.generate_text_stream(
                    title_prompt
                )
            ]
            title = "".join(chunks).strip()

            if not title or len(title) > 200:
                return

            self._repository.set_auto_title(chat_id, title)
        except Exception:
            # Automatic naming is optional and must never fail the chat turn.
            return
