"""Memory-bounded collection of Gmail inbox threads by their newest message."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from zoneinfo import ZoneInfo


logger = logging.getLogger(__name__)


class MailWorkflowClient(Protocol):
    """The narrow workflow-client surface used by the collector."""

    async def set_mail_provider(self, provider: str) -> None: ...

    async def get_mail_provider_stats(self) -> dict[str, object]: ...

    async def get_mail_messages(
        self,
        category: str,
        *,
        since: datetime | None = None,
        before: datetime | None = None,
    ) -> list[dict[str, object]]: ...

    async def get_mail_messages_by_thread(
        self, thread_id: str
    ) -> list[dict[str, object]]: ...


@dataclass(frozen=True)
class MailHeader:
    """The metadata retained for one message; no body or attachment data."""

    message_id: str
    thread_id: str | None
    internal_date: datetime
    subject: str
    sender: str
    is_read: bool

    @classmethod
    def from_result(cls, value: Mapping[str, object]) -> "MailHeader":
        return cls(
            message_id=value["message_id"],  # type: ignore[arg-type]
            thread_id=value["thread_id"],  # type: ignore[arg-type]
            internal_date=_parse_datetime(value["internal_date"]),
            subject=value["subject"],  # type: ignore[arg-type]
            sender=value["sender"],  # type: ignore[arg-type]
            is_read=value["is_read"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class CollectedThread:
    """One thread handed to the next organizer stage."""

    thread_id: str
    headers: tuple[MailHeader, ...]


class InboxThreadCollector:
    """Yield each inbox thread once, in the month of its newest message.

    The collector deliberately holds only message headers.  It does not call
    ``mail.get_mail`` or attachment capabilities; those belong to AP3.
    """

    def __init__(
        self,
        client: MailWorkflowClient,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now().astimezone(),
        timezone: ZoneInfo = ZoneInfo("Europe/Berlin"),
    ) -> None:
        self._client = client
        self._clock = clock
        self._timezone = timezone

    async def collect(self) -> AsyncIterator[CollectedThread]:
        """Select Gmail and yield collected threads in chronological months."""
        workflow_now = _require_aware(
            self._clock(), "Workflow clock returned a naive datetime."
        )
        await self._client.set_mail_provider("gmail")
        stats = await self._client.get_mail_provider_stats()
        if stats["inbox_messages_count"] == 0:
            return

        oldest = _parse_datetime(stats["oldest_message_date"])
        start = oldest.astimezone(self._timezone)
        end = workflow_now.astimezone(self._timezone)
        if start >= end:
            return

        pending: dict[str, dict[str, tuple[MailHeader, ...]]] = {}
        processed_thread_ids: set[str] = set()

        window_start = start
        while window_start < end:
            window_end = min(_next_month_start(window_start, self._timezone), end)
            month = _month_key(window_start)
            messages = await self._client.get_mail_messages(
                "INBOX", since=window_start, before=window_end
            )

            for raw_message in messages:
                inbox_header = MailHeader.from_result(raw_message)
                thread_id = inbox_header.thread_id
                if thread_id in processed_thread_ids:
                    continue
                processed_thread_ids.add(thread_id)

                headers = tuple(
                    MailHeader.from_result(header)
                    for header in await self._client.get_mail_messages_by_thread(thread_id)
                )
                newest = max(header.internal_date for header in headers)
                target_month = _month_key(newest.astimezone(self._timezone))
                pending.setdefault(target_month, {})[thread_id] = headers

            for thread_id, headers in pending.pop(month, {}).items():
                yield CollectedThread(thread_id=thread_id, headers=headers)
            window_start = window_end

        if pending:
            logger.warning(
                "Yielding %d thread(s) assigned after workflow snapshot %s: %s.",
                sum(len(bucket) for bucket in pending.values()),
                end.isoformat(),
                ", ".join(sorted(pending)),
            )
            for target_month in sorted(pending):
                for thread_id, headers in pending[target_month].items():
                    yield CollectedThread(thread_id=thread_id, headers=headers)


def _parse_datetime(value: object) -> datetime:
    return _require_aware(
        datetime.fromisoformat(value.replace("Z", "+00:00")),  # type: ignore[union-attr]
        "Mail timestamp must be timezone-aware.",
    )


def _require_aware(value: datetime, message: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(message)
    return value


def _next_month_start(value: datetime, timezone: ZoneInfo) -> datetime:
    local = value.astimezone(timezone)
    if local.month == 12:
        return datetime(local.year + 1, 1, 1, tzinfo=timezone)
    return datetime(local.year, local.month + 1, 1, tzinfo=timezone)


def _month_key(value: datetime) -> str:
    return f"{value.year:04d}-{value.month:02d}"
