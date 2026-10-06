"""Persistent chat and message operations."""

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload, selectin_polymorphic, sessionmaker

from app.user_config import get_user_config
from app.persistence.models import Agent, Attachment, Chat, Message, ProgressMessage, TextMessage



class ChatRepository:
    """Store and retrieve persistent Avalon conversations."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @property
    def session_factory(self) -> sessionmaker[Session]:
        """Expose the shared factory for collaborating repositories."""
        return self._session_factory

    def create_chat(self, title: str, agent_id: int | None = None) -> Chat:
        """Create one persistent chat."""
        normalized_title = self._validate_title(title)

        with self._session_factory() as session:
            chat = Chat(
                title=normalized_title,
                agent_id=self._resolve_agent_id(session, agent_id),
            )
            session.add(chat)
            session.commit()
            session.refresh(chat)
            return chat

    def create_chat_with_message(
        self,
        title: str,
        role: str,
        content: str,
        agent_id: int | None = None,
    ) -> Chat:
        """Create a chat and its first message atomically."""
        normalized_title = self._validate_title(title)
        self._validate_message(role, content)

        with self._session_factory() as session:
            chat = Chat(
                title=normalized_title,
                agent_id=self._resolve_agent_id(session, agent_id),
                next_message_seq=2,
            )
            message = TextMessage(
                chat=chat,
                role=role,
                content=content,
                seq=1,
            )
            session.add_all([chat, message])
            session.commit()
            session.refresh(chat)
            return chat

    def add_message(
        self,
        chat_id: int,
        role: str,
        content: str,
    ) -> Message:
        """Append one complete message to a persistent chat."""
        self._validate_message(role, content)

        with self._session_factory() as session:
            next_sequence = session.execute(
                update(Chat)
                .where(Chat.id == chat_id)
                .values(next_message_seq=Chat.next_message_seq + 1)
                .returning(Chat.next_message_seq)
            ).scalar_one_or_none()
            if next_sequence is None:
                raise ValueError(f"Chat {chat_id} does not exist.")

            message = TextMessage(
                chat_id=chat_id,
                role=role,
                content=content,
                seq=next_sequence - 1,
            )
            session.add(message)
            session.commit()
            session.refresh(message)
            return message

    def update_message_content(
        self,
        message_id: int,
        content: str,
    ) -> bool:
        """Replace the content of one existing message."""
        if not content:
            raise ValueError("Message content must not be empty.")

        with self._session_factory() as session:
            message = session.get(TextMessage, message_id)
            if message is None:
                return False

            message.content = content
            session.commit()
            return True

    def get_chat(self, chat_id: int) -> Chat | None:
        """Return one chat or None when it does not exist."""
        with self._session_factory() as session:
            return session.scalar(
                select(Chat)
                .where(Chat.id == chat_id)
                .options(selectinload(Chat.agent))
            )

    def get_agent_by_key(self, key: str) -> Agent | None:
        """Resolve one reconciled agent by its configured key."""
        with self._session_factory() as session:
            return session.scalar(select(Agent).where(Agent.key == key))

    def get_agent_by_id(self, agent_id: int) -> Agent | None:
        """Resolve one reconciled agent by persistent id."""
        with self._session_factory() as session:
            return session.get(Agent, agent_id)

    def assign_agent(self, chat_id: int, agent_id: int) -> bool:
        """Atomically replace a chat agent."""
        with self._session_factory() as session:
            result = session.execute(
                update(Chat)
                .where(Chat.id == chat_id)
                .values(agent_id=agent_id)
            )
            session.commit()
            return result.rowcount == 1

    def unload_agent(self, chat_id: int) -> bool:
        """Atomically restore the default agent."""
        with self._session_factory() as session:
            default_agent_key = get_user_config().chat_default_agent_key
            default_agent = session.scalar(select(Agent).where(Agent.key == default_agent_key))
            if default_agent is None:
                return False
            result = session.execute(
                update(Chat)
                .where(Chat.id == chat_id)
                .values(agent_id=default_agent.id)
            )
            session.commit()
            return result.rowcount == 1

    def get_agent_id(self, chat_id: int) -> int | None:
        """Resolve the agent currently authorizing one chat."""
        with self._session_factory() as session:
            chat = session.get(Chat, chat_id)
            if chat is None:
                return None
            return None if chat is None else chat.agent_id

    def get_messages(self, chat_id: int) -> list[Message]:

        """Return the complete chat history in chronological order."""
        with self._session_factory() as session:
            statement = (
                select(Message)
                .where(Message.chat_id == chat_id)
                .order_by(Message.created_at, Message.id)
                .options(
                    selectin_polymorphic(Message, [TextMessage, ProgressMessage]),
                    selectinload(TextMessage.attachments),
                    selectinload(ProgressMessage.workflow_execution),
                )
            )
            return list(session.scalars(statement))

    def get_text_messages(self, chat_id: int) -> list[TextMessage]:
        """Return only normal text messages, for LLM context and titles."""
        with self._session_factory() as session:
            return list(session.scalars(
                select(TextMessage)
                .where(TextMessage.chat_id == chat_id)
                .order_by(TextMessage.created_at, TextMessage.id)
            ))

    def get_attachments_for_messages(
        self, message_ids: list[int]
    ) -> dict[int, list[Attachment]]:
        """Return attachment metadata grouped by message id."""
        if not message_ids:
            return {}
        with self._session_factory() as session:
            messages = session.scalars(
                select(TextMessage)
                .where(TextMessage.id.in_(message_ids))
                .options(selectinload(TextMessage.attachments))
            )
            return {
                message.id: list(message.attachments)
                for message in messages
            }

    def get_context_messages(
        self,
        chat_id: int,
        limit: int = 100,
    ) -> list[TextMessage]:
        """Return the latest normal text messages in chronological order."""
        if limit < 1:
            raise ValueError("Context message limit must be positive.")

        with self._session_factory() as session:
            statement = (
                select(TextMessage)
                .where(TextMessage.chat_id == chat_id)
                .order_by(TextMessage.created_at.desc(), TextMessage.id.desc())
                .limit(limit)
            )
            messages = list(session.scalars(statement))
            messages.reverse()
            return messages

    def compare_and_set_compression_state(
        self,
        chat_id: int,
        expected_version: int,
        compressed_context: str,
        compressed_through_seq: int,
    ) -> bool:
        """Persist a compression result only if its snapshot is current."""
        with self._session_factory() as session:
            result = session.execute(
                update(Chat)
                .where(
                    Chat.id == chat_id,
                    Chat.compression_version == expected_version,
                    Chat.compression_error_code.is_(None),
                )
                .values(
                    compressed_context=compressed_context,
                    compressed_through_seq=compressed_through_seq,
                    compression_version=expected_version + 1,
                )
            )
            session.commit()
            return result.rowcount == 1

    def set_compression_error_if_version(
        self,
        chat_id: int,
        expected_version: int,
        error_code: str,
    ) -> bool:
        """Persist a terminal compression error for a current job snapshot."""
        with self._session_factory() as session:
            result = session.execute(
                update(Chat)
                .where(
                    Chat.id == chat_id,
                    Chat.compression_version == expected_version,
                    Chat.compression_error_code.is_(None),
                )
                .values(compression_error_code=error_code)
            )
            session.commit()
            return result.rowcount == 1

    def list_chats(self) -> list[Chat]:
        """Return all chats ordered by most recent message activity."""
        with self._session_factory() as session:
            last_message_at = func.max(Message.created_at)
            statement = (
                select(Chat)
                .join(Message, Message.chat_id == Chat.id)
                .group_by(Chat.id)
                .order_by(last_message_at.desc(), Chat.id.desc())
                .options(selectinload(Chat.agent))
            )
            return list(session.scalars(statement))

    def rename_chat(self, chat_id: int, title: str) -> Chat | None:
        """Rename a chat and permanently mark its title as manual."""
        normalized_title = self._validate_title(title)

        with self._session_factory() as session:
            chat = session.scalar(
                select(Chat)
                .where(Chat.id == chat_id)
                .options(selectinload(Chat.agent))
            )
            if chat is None:
                return None

            chat.title = normalized_title
            chat.title_is_manual = True
            session.commit()
            session.refresh(chat)
            return chat

    def set_pinned(self, chat_id: int, pinned: bool) -> Chat | None:
        """Persist the pinned state of one chat."""
        with self._session_factory() as session:
            chat = session.scalar(
                select(Chat)
                .where(Chat.id == chat_id)
                .options(selectinload(Chat.agent))
            )
            if chat is None:
                return None

            chat.pinned = pinned
            session.commit()
            session.refresh(chat)
            return chat

    def claim_auto_title_attempt(self, chat_id: int) -> bool:
        """Atomically claim the one allowed automatic-title attempt."""

        with self._session_factory() as session:
            chat = session.get(Chat, chat_id)
            if (
                chat is None
                or chat.title_is_manual
                or chat.auto_title_attempted
            ):
                return False

            chat.auto_title_attempted = True
            session.commit()
            return True

    def set_auto_title(self, chat_id: int, title: str) -> bool:
        """Store a generated title unless a manual title now exists."""
        normalized_title = self._validate_title(title)

        with self._session_factory() as session:
            chat = session.get(Chat, chat_id)
            if chat is None or chat.title_is_manual:
                return False

            chat.title = normalized_title
            session.commit()
            return True

    def delete_chat(self, chat_id: int) -> bool:
        """Physically delete a chat and its messages."""
        with self._session_factory() as session:
            chat = session.get(Chat, chat_id)
            if chat is None:
                return False

            session.delete(chat)
            session.commit()
            return True

    @staticmethod
    def _resolve_agent_id(session: Session, agent_id: int | None) -> int:
        """Use the reconciled default agent for ordinary chats."""
        if agent_id is not None:
            return agent_id
        default_agent_key = get_user_config().chat_default_agent_key
        agent = session.scalar(select(Agent).where(Agent.key == default_agent_key))
        if agent is None:
            raise RuntimeError("The default agent has not been reconciled.")
        return agent.id

    @staticmethod
    def _validate_message(role: str, content: str) -> None:
        """Validate persistent message invariants."""
        if role not in {"user", "assistant"}:
            raise ValueError("Message role must be 'user' or 'assistant'.")

        if not content:
            raise ValueError("Message content must not be empty.")

    @staticmethod
    def _validate_title(title: str) -> str:
        """Normalize and validate a persistent chat title."""
        normalized = title.strip()

        if not normalized:
            raise ValueError("Chat title must not be empty.")

        if len(normalized) > 200:
            raise ValueError("Chat title must not exceed 200 characters.")

        return normalized
