"""Provider contracts and defined mail failures."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.mail.models import Mail, MailMessage, MailProviderStats


class MailError(RuntimeError):
    """Base error exposed by the local mail capability."""


class NoActiveMailProviderError(MailError):
    pass


class UnsupportedMailProviderError(MailError):
    pass


class MailAuthenticationError(MailError):
    pass


class MailConnectionError(MailError):
    pass


class MailProtocolError(MailError):
    pass


class MailProvider(Protocol):
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def get_provider_stats(self) -> MailProviderStats: ...
    def get_messages(self, category: str, since: datetime | None, before: datetime | None) -> list[MailMessage]: ...
    def get_messages_by_thread(self, thread_id: str) -> list[MailMessage]: ...
    def get_mail(self, message_id: str, as_text: bool = True) -> Mail: ...
    def get_categories(self) -> list[str]: ...
