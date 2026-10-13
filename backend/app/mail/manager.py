"""Lifecycle and active-provider selection for read-only mail."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable

from app.mail.models import Mail, MailMessage, MailProviderStats
from app.mail.providers import MailProvider, NoActiveMailProviderError, UnsupportedMailProviderError
from app.state import AvalonState


logger = logging.getLogger(__name__)


class MailProviderManager:
    def __init__(self, state_provider: Callable[[], AvalonState], factories: dict[str, Callable[[], MailProvider]]) -> None:
        self._state_provider = state_provider
        self._factories = factories
        self._providers: dict[str, MailProvider] = {}

    def set_provider(self, provider: str) -> None:
        state = self._state_provider()
        if state.active_mail_provider == provider:
            self._active().invalidate_categories_cache()
            return
        factory = self._factories.get(provider)
        if factory is None:
            raise UnsupportedMailProviderError(f"Mail provider '{provider}' is not implemented.")
        candidate = self._providers.get(provider) or factory()
        candidate.connect()
        previous_name = state.active_mail_provider
        previous = self._providers.get(previous_name) if previous_name else None
        self._providers[provider] = candidate
        state.active_mail_provider = provider
        candidate.invalidate_categories_cache()
        if previous is not None:
            try:
                previous.disconnect()
            except Exception:
                logger.warning(
                    "Could not disconnect inactive mail provider '%s'.",
                    previous_name,
                    exc_info=True,
                )

    def get_provider_stats(self) -> MailProviderStats:
        return self._active().get_provider_stats()

    def get_messages(self, category: str, since: datetime | None, before: datetime | None) -> list[MailMessage]:
        return self._active().get_messages(category, since, before)

    def get_messages_by_thread(self, thread_id: str) -> list[MailMessage]:
        return self._active().get_messages_by_thread(thread_id)

    def get_mail(self, message_id: str, as_text: bool = True) -> Mail:
        return self._active().get_mail(message_id, as_text)

    def get_categories(self) -> list[str]:
        return self._active().get_categories()

    def create_categories(self, categories: list[str]) -> None:
        self._active().create_categories(categories)

    def set_categories(self, message_id: str, categories: list[str], archive: bool = False) -> None:
        self._active().set_categories(message_id, categories, archive)

    def unset_categories(self, message_id: str, categories: list[str]) -> None:
        self._active().unset_categories(message_id, categories)

    def _active(self) -> MailProvider:
        name = self._state_provider().active_mail_provider
        if name is None or name not in self._providers:
            raise NoActiveMailProviderError("No mail provider is active.")
        return self._providers[name]
