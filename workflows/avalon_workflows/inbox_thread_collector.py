"""Memory-bounded collection of Gmail inbox threads by their newest message."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
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
        message_id = value.get("message_id")
        internal_date = _parse_datetime(value.get("internal_date"))
        if not isinstance(message_id, str) or not message_id:
            raise ValueError("Mail header has no valid message_id.")
        if internal_date is None:
            raise ValueError("Mail header has no valid internal_date.")

        thread_id = value.get("thread_id")
        if not isinstance(thread_id, str) or not thread_id:
            thread_id = None
        subject = value.get("subject")
        sender = value.get("sender")
        is_read = value.get("is_read")
        return cls(
            message_id=message_id,
            thread_id=thread_id,
            internal_date=internal_date,
            subject=subject if isinstance(subject, str) else "",
            sender=sender if isinstance(sender, str) else "",
            is_read=is_read if isinstance(is_read, bool) else False,
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
        if not isinstance(stats, Mapping):
            raise ValueError("Mail provider returned invalid statistics.")
        inbox_count = _inbox_count(stats)
        if inbox_count == 0:
            return

        oldest = _parse_datetime(stats.get("oldest_message_date"))
        if oldest is None:
            raise ValueError("Mail provider reported inbox messages without oldest_message_date.")
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
            try:
                messages = await self._client.get_mail_messages(
                    "INBOX", since=window_start, before=window_end
                )
                if not isinstance(messages, list):
                    raise ValueError("Mail provider returned invalid inbox messages.")
            except Exception:
                logger.exception("Could not collect inbox messages for month %s.", month)
                raise

            for raw_message in messages:
                try:
                    inbox_header = MailHeader.from_result(raw_message)
                    thread_id = inbox_header.thread_id
                    if thread_id is None:
                        raise ValueError("Inbox message has no thread_id.")
                    if thread_id in processed_thread_ids:
                        continue
                    processed_thread_ids.add(thread_id)

                    headers = tuple(
                        MailHeader.from_result(header)
                        for header in await self._client.get_mail_messages_by_thread(thread_id)
                    )
                    if not headers:
                        raise ValueError("Thread has no message headers.")
                    newest = max(header.internal_date for header in headers)
                    target_month = _month_key(newest.astimezone(self._timezone))
                    pending.setdefault(target_month, {})[thread_id] = headers
                except Exception:
                    logger.exception(
                        "Skipping unreadable mail thread %s while collecting month %s.",
                        _thread_id_for_log(raw_message),
                        month,
                    )

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


def _inbox_count(stats: Mapping[str, object]) -> int:
    value = stats.get("inbox_messages_count")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Mail provider returned an invalid inbox_messages_count.")
    return value


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _require_aware(value, "Mail timestamp must be timezone-aware.")
    if not isinstance(value, str):
        raise ValueError("Mail timestamp must be an ISO-8601 string.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Mail timestamp must be ISO-8601.") from exc
    return _require_aware(parsed, "Mail timestamp must be timezone-aware.")


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


def _thread_id_for_log(value: Any) -> object:
    return value.get("thread_id") if isinstance(value, Mapping) else "<invalid>"
