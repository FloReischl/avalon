"""Persistent Avalon chat models."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for Avalon persistence models."""


class Chat(Base):
    """One persistent conversation."""

    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    title_is_manual: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    auto_title_attempted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    pinned: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    compressed_context: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default='{"summaries":[],"stars":[]}',
        server_default='{"summaries":[],"stars":[]}',
    )
    compressed_through_seq: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default="0",
    )
    compression_version: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default="0",
    )
    compression_error_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    next_message_seq: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
        server_default="1",
    )
    created_at: Mapped[datetime] = mapped_column(

        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
    )


class Message(Base):
    """One persistent user or assistant message."""

    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_chat_id_created_at", "chat_id", "created_at"),
        Index("ix_messages_chat_id_seq", "chat_id", "seq", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    seq: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    chat: Mapped[Chat] = relationship(back_populates="messages")
