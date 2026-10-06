"""Text-chat application service."""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from app.agents_config import AgentConfig
from app.commands import CommandContext, CommandRegistry, CommandRequest, parse_command
from app.persistence.chat_repository import ChatRepository

from app.user_config import get_user_config
from app.avatars_config import AvatarConfig
from app.runtime.base import ModelRuntime
from app.services.context_compression import (
    ContextCompressionService,
    build_active_context,
    parse_compressed_context,
)
from app.services.tool_runner import ToolRunner


class ChatNotFoundError(Exception):
    """Raised when a requested persistent chat does not exist."""


class ChatCompressionFailedError(Exception):
    """Raised when a chat has reached its terminal compression error state."""


@dataclass(frozen=True, slots=True)
class ChatTurn:
    """Prepared persistent chat turn ready for response generation."""

    chat_id: int
    messages: list[dict[str, str]]
    command_response: str | None = None
    command_request: CommandRequest | None = None
    authorization_source_label: str = "Chat: Unbenannt"


class ChatService:
    """Coordinate persistent text-chat turns and model generation."""

    def __init__(
        self,
        runtime: ModelRuntime,
        repository: ChatRepository,
        avatar: AvatarConfig | None = None,
        command_registry: CommandRegistry | None = None,
        compression_service: ContextCompressionService | None = None,
        task_scheduler: Callable[[Any], Any] | None = None,
        tool_runner: ToolRunner | None = None,
        agents: tuple[AgentConfig, ...] = (),
    ) -> None:

        self._runtime = runtime
        self._repository = repository
        self._avatar = avatar
        self._agents = agents
        self._command_registry = command_registry or CommandRegistry()
        self._compression_service = compression_service or ContextCompressionService(
            runtime,
            repository,
            avatar,
            agents,
        )

        self._task_scheduler = task_scheduler or asyncio.create_task
        self._compression_tasks: set[asyncio.Task[object]] = set()
        self._tool_runner = tool_runner

    def start_turn(
        self,
        chat_id: int | None,
        message: str,
    ) -> ChatTurn:
        """Persist the user input and prepare bounded model context."""
        if chat_id is None:
            title = datetime.now().strftime("New %Y-%m-%d %H:%M:%S")
            try:
                agent_key = get_user_config().chat_default_agent_key
            except RuntimeError:
                agent_key = "default"
            agent = self._repository.get_agent_by_key(agent_key)
            if agent is None:
                raise RuntimeError("Configured chat default agent is missing.")
            chat = self._repository.create_chat_with_message(
                title,
                "user",
                message,
                agent.id,
            )
            chat_id = chat.id
        else:
            chat = self._repository.get_chat(chat_id)
            if chat is None:
                raise ChatNotFoundError(f"Chat {chat_id} does not exist.")
            if chat.compression_error_code is not None:
                raise ChatCompressionFailedError(
                    chat.compression_error_code
                )

            self._repository.add_message(chat_id, "user", message)

        command_request = parse_command(message)
        if (
            command_request is not None
            and self._command_registry.contains(command_request)
        ):
            return ChatTurn(
                chat_id=chat_id,
                messages=[],
                command_request=command_request,
            )

        chat = self._repository.get_chat(chat_id)
        assert chat is not None
        context = self._repository.get_text_messages(chat_id)
        messages = build_active_context(
            context,
            parse_compressed_context(chat.compressed_context),
            chat.compressed_through_seq,
            self._context_identity(chat.agent_id),
        )

        return ChatTurn(
            chat_id=chat_id,
            messages=messages,
            authorization_source_label=self._authorization_source_label(chat.title),
        )

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
                turn.command_request,
                CommandContext(chat_id=turn.chat_id),
            )

            yield command_response
            self._repository.add_message(
                turn.chat_id,
                "assistant",
                command_response,
            )
            return

        response_chunks: list[str] = []

        if self._tool_runner is not None:
            agent_id = self._repository.get_agent_id(
                turn.chat_id
            )
            assert agent_id is not None
            chunks = self._tool_runner.stream_response(
                agent_id, turn.messages, turn.authorization_source_label, turn.chat_id
            )

        else:
            chunks = self._runtime.generate_text_stream(turn.messages)

        async for chunk in chunks:
            response_chunks.append(chunk)
            yield chunk

        response = "".join(response_chunks)
        if response:
            self._repository.add_message(turn.chat_id, "assistant", response)

    def persist_stream_error(self, turn: ChatTurn, error: Exception) -> None:
        """Persist one safe visible error without leaking technical diagnostics."""
        del error
        self._repository.add_message(
            turn.chat_id, "assistant", "Die Antwort konnte nicht erzeugt werden."
        )

    def _context_identity(self, agent_id: int | None):
        if agent_id is None:
            return self._avatar

        persisted_agent = self._repository.get_agent_by_id(agent_id)
        if persisted_agent is None:
            raise RuntimeError(f"Agent {agent_id} does not exist.")

        normalized = persisted_agent.key.casefold()
        configured_agent = next(
            (
                agent
                for agent in self._agents
                if agent.key.casefold() == normalized
            ),
            None,
        )
        if configured_agent is None:
            raise RuntimeError(
                f"Agent '{persisted_agent.key}' is not configured."
            )
        return configured_agent

    async def finalize_turn(self, turn: ChatTurn) -> None:
        """Run optional post-response work after the client receives done."""

        self._schedule_compression(turn.chat_id)

        if turn.command_response is None and turn.command_request is None:
            try:
                await self._try_auto_title(turn.chat_id)
            except Exception:
                # Optional post-response work must never affect a completed turn.
                pass

    def _schedule_compression(self, chat_id: int) -> None:
        """Start compression without awaiting it in the completed turn path."""
        task = self._task_scheduler(
            self._compression_service.compress_if_needed(chat_id)
        )
        if isinstance(task, asyncio.Task):
            self._compression_tasks.add(task)
            task.add_done_callback(self._compression_tasks.discard)

    async def _try_auto_title(self, chat_id: int) -> None:
        """Attempt automatic title generation after roundtrip two."""
        messages = self._repository.get_text_messages(chat_id)

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

    @staticmethod
    def _authorization_source_label(title: str) -> str:
        """Create the compact chat label shown by the permission inbox."""
        compact = " ".join(title.split())
        return f"Chat: {compact[:60]}"
