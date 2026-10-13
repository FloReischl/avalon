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
class MailProviderStats:
    all_messages_count: int
    inbox_messages_count: int
    inbox_unread_count: int
    oldest_message_date: datetime | None
    newest_message_date: datetime | None
