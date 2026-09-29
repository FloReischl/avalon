"""Persistence operations for immutable Avalon attachments."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.persistence.models import Attachment, Message


class AttachmentRepository:
    """Store attachments and link them to already persisted messages."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_and_attach(
        self,
        message_id: int,
        file_name: str,
        original_file_name: str,
        mime_type: str,
        size: int,
    ) -> Attachment | None:
        """Atomically persist one attachment and its message relation."""
        with self._session_factory() as session:
            message = session.get(Message, message_id)
            if message is None:
                return None
            attachment = Attachment(
                file_name=file_name,
                original_file_name=original_file_name,
                mime_type=mime_type,
                size=size,
            )
            message.attachments.append(attachment)
            session.commit()
            session.refresh(attachment)
            return attachment

    def get(self, attachment_id: int) -> Attachment | None:
        with self._session_factory() as session:
            return session.get(Attachment, attachment_id)

    def get_for_message(self, message_id: int) -> list[Attachment]:
        with self._session_factory() as session:
            message = session.scalar(
                select(Message)
                .where(Message.id == message_id)
                .options(selectinload(Message.attachments))
            )
            return [] if message is None else list(message.attachments)
