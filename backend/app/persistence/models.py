"""Persistent Avalon chat models."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for Avalon persistence models."""


class Agent(Base):
    """One configured chat and authorization agent."""

    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)


class PermissionCatalog(Base):
    """One available concrete permission implementation."""

    __tablename__ = "permission_catalog"
    __table_args__ = (UniqueConstraint("context", "key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    context: Mapped[str] = mapped_column(String(100), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)


class PermissionSet(Base):
    """The maximum grantable permission set for one agent."""

    __tablename__ = "permission_sets"
    __table_args__ = (
        UniqueConstraint("agent_id", "permission_catalog_id", "scope"),
        CheckConstraint(
            "validity_type IN ('permanent', 'duration', 'range')",
            name="ck_permission_sets_validity_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    permission_catalog_id: Mapped[int] = mapped_column(
        ForeignKey("permission_catalog.id", ondelete="CASCADE"), nullable=False
    )
    scope: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    validity_type: Mapped[str] = mapped_column(String(16), nullable=False)
    default_expiry: Mapped[int] = mapped_column(Integer, nullable=False)


class PermissionGrant(Base):
    """One persisted authorization grant."""

    __tablename__ = "permission_grants"

    id: Mapped[int] = mapped_column(primary_key=True)
    permission_set_id: Mapped[int] = mapped_column(
        ForeignKey("permission_sets.id", ondelete="CASCADE"), nullable=False
    )
    valid_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    valid_to: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    range: Mapped[str | None] = mapped_column(Text, nullable=True)


class Chat(Base):
    """One persistent conversation."""

    __tablename__ = "chats"
    __table_args__ = (CheckConstraint("agent_id IS NOT NULL", name="ck_chats_agent_id_required"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(
        ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False
    )
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
    agent: Mapped["Agent"] = relationship()


class Message(Base):
    """One chronologically positioned conversation element."""

    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_chat_id_created_at", "chat_id", "created_at"),
        Index("ix_messages_chat_id_seq", "chat_id", "seq", unique=True),
        UniqueConstraint("chat_id", "invocation_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    invocation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    seq: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    chat: Mapped[Chat] = relationship(back_populates="messages")
    __mapper_args__ = {"polymorphic_on": kind, "polymorphic_identity": "message"}


class TextMessage(Message):
    """A normal user or assistant text message."""

    __tablename__ = "text_messages"

    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[list["Attachment"]] = relationship(
        secondary="message_attachments",
        back_populates="messages",
    )

    __mapper_args__ = {"polymorphic_identity": "text"}


class ProgressMessage(Message):
    """The stable visible container for one workflow execution's progress."""

    __tablename__ = "progress_messages"

    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
    messages: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]", server_default="[]"
    )
    workflow_execution: Mapped["WorkflowExecution"] = relationship(
        back_populates="progress_message", uselist=False, cascade="all, delete-orphan"
    )

    __mapper_args__ = {"polymorphic_identity": "progress"}


class WorkflowExecution(Base):
    """Persisted lifecycle truth for one workflow execution."""

    __tablename__ = "workflow_executions"
    __table_args__ = (
        CheckConstraint(
            "state IN ('running', 'pending', 'completed', 'failed', 'aborted')",
            name="ck_workflow_executions_state",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    progress_message_id: Mapped[int] = mapped_column(
        ForeignKey("progress_messages.message_id", ondelete="CASCADE"), nullable=False, unique=True
    )
    workflow_key: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    progress_message: Mapped[ProgressMessage] = relationship(
        back_populates="workflow_execution"
    )


class Attachment(Base):
    """One immutable file artifact managed by Avalon."""

    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_name: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)
    original_file_name: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    messages: Mapped[list[TextMessage]] = relationship(
        secondary="message_attachments",
        back_populates="attachments",
    )


class MessageAttachment(Base):
    """A relation between a message and an immutable attachment."""

    __tablename__ = "message_attachments"

    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True
    )
    attachment_id: Mapped[int] = mapped_column(
        ForeignKey("attachments.id", ondelete="RESTRICT"), primary_key=True
    )
