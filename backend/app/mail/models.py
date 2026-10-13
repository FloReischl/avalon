"""Public, provider-neutral mail value objects."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MailMessage:
    message_id: str
    thread_id: str | None
    internal_date: datetime
    subject: str
    sender: str
    is_read: bool


@dataclass(frozen=True)
class MailSender:
    name: str
    email_address: str


@dataclass(frozen=True)
class MailBodyPart:
    mime_type: str
    content: str


@dataclass(frozen=True)
class MailAttachment:
    name: str
    id: str
    mime_type: str


@dataclass(frozen=True)
class Mail:
    message_id: str
    is_read: bool
    internal_date: datetime
    subject: str
    sender: MailSender
    thread_id: str | None
    body: list[MailBodyPart]
    attachments: list[MailAttachment]


@dataclass(frozen=True)
class MailProviderStats:
    all_messages_count: int
    inbox_messages_count: int
    inbox_unread_count: int
    oldest_message_date: datetime | None
    newest_message_date: datetime | None
