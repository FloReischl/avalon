"""Persistent chat and message operations."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.persistence.models import Chat, Message


class ChatRepository:
    """Store and retrieve persistent Avalo conversations."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_chat(self, title: str) -> Chat:
        """Create one persistent chat."""
        normalized_title = self._validate_title(title)

        with self._session_factory() as session:
            chat = Chat(title=normalized_title)
            session.add(chat)
            session.commit()
            session.refresh(chat)
            return chat

    def create_chat_with_message(
        self,
        title: str,
        role: str,
        content: str,
    ) -> Chat:
        """Create a chat and its first message atomically."""
        normalized_title = self._validate_title(title)
        self._validate_message(role, content)

        with self._session_factory() as session:
            chat = Chat(title=normalized_title)
            message = Message(
                chat=chat,
                role=role,
                content=content,
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
            message = Message(
                chat_id=chat_id,
                role=role,
                content=content,
            )
            session.add(message)
            session.commit()
            session.refresh(message)
            return message

    def get_chat(self, chat_id: int) -> Chat | None:
        """Return one chat or None when it does not exist."""
        with self._session_factory() as session:
            return session.get(Chat, chat_id)

    def get_messages(self, chat_id: int) -> list[Message]:
        """Return the complete chat history in chronological order."""
        with self._session_factory() as session:
            statement = (
                select(Message)
                .where(Message.chat_id == chat_id)
                .order_by(Message.created_at, Message.id)
            )
            return list(session.scalars(statement))

    def get_context_messages(
        self,
        chat_id: int,
        limit: int = 100,
    ) -> list[Message]:
        """Return the latest messages in chronological order."""
        if limit < 1:
            raise ValueError("Context message limit must be positive.")

        with self._session_factory() as session:
            statement = (
                select(Message)
                .where(Message.chat_id == chat_id)
                .order_by(Message.created_at.desc(), Message.id.desc())
                .limit(limit)
            )
            messages = list(session.scalars(statement))
            messages.reverse()
            return messages

    def list_chats(self) -> list[Chat]:
        """Return all chats ordered by most recent message activity."""
        with self._session_factory() as session:
            last_message_at = func.max(Message.created_at)
            statement = (
                select(Chat)
                .join(Message, Message.chat_id == Chat.id)
                .group_by(Chat.id)
                .order_by(last_message_at.desc(), Chat.id.desc())
            )
            return list(session.scalars(statement))

    def rename_chat(self, chat_id: int, title: str) -> Chat | None:
        """Rename a chat and permanently mark its title as manual."""
        normalized_title = self._validate_title(title)

        with self._session_factory() as session:
            chat = session.get(Chat, chat_id)
            if chat is None:
                return None

            chat.title = normalized_title
            chat.title_is_manual = True
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