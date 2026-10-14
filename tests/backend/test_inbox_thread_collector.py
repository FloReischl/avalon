"""Offline contracts for the Gmail inbox-organizer AP2 collector."""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "workflows"))

from avalon_workflows.inbox_thread_collector import InboxThreadCollector


def stamp(value: str) -> str:
    return value.replace(" ", "T") + "+00:00"


def header(message_id: str, thread_id: str | None, when: str) -> dict[str, object]:
    return {
        "message_id": message_id,
        "thread_id": thread_id,
        "internal_date": stamp(when),
        "subject": "Subject",
        "sender": "sender@example.test",
        "is_read": True,
    }


class FakeClient:
    def __init__(self, *, oldest: str | None, inbox: dict[tuple[str, str], list[dict[str, object]]], threads: dict[str, object], inbox_count: int | None = None) -> None:
        self.stats = {
            "inbox_messages_count": inbox_count if inbox_count is not None else sum(len(value) for value in inbox.values()),
            "oldest_message_date": stamp(oldest) if oldest else None,
        }
        self.inbox = inbox
        self.threads = threads
        self.calls: list[tuple[str, object]] = []

    async def set_mail_provider(self, provider: str) -> None:
        self.calls.append(("set_provider", provider))

    async def get_mail_provider_stats(self) -> dict[str, object]:
        self.calls.append(("stats", None))
        return self.stats

    async def get_mail_messages(self, category: str, *, since: datetime | None = None, before: datetime | None = None) -> list[dict[str, object]]:
        assert category == "INBOX"
        assert since is not None and before is not None
        key = (since.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M"), before.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M"))
        self.calls.append(("messages", key))
        result = self.inbox.get(key, [])
        if isinstance(result, Exception):
            raise result
        return result

    async def get_mail_messages_by_thread(self, thread_id: str) -> list[dict[str, object]]:
        self.calls.append(("thread", thread_id))
        result = self.threads[thread_id]
        if isinstance(result, Exception):
            raise result
        return result  # type: ignore[return-value]


async def collected(client: FakeClient, now: str) -> list:
    collector = InboxThreadCollector(
        client,
        clock=lambda: datetime.fromisoformat(stamp(now)),
        timezone=ZoneInfo("UTC"),
    )
    return [item async for item in collector.collect()]


def test_collects_contiguous_months_across_year_boundary_in_target_month() -> None:
    client = FakeClient(
        oldest="2024-12-17 12:00",
        inbox={
            ("2024-12-17 12:00", "2025-01-01 00:00"): [header("one", "thread-1", "2024-12-20 10:00")],
            ("2025-01-01 00:00", "2025-02-01 00:00"): [header("two", "thread-1", "2025-01-03 10:00"), header("three", "thread-2", "2025-01-31 10:00")],
            ("2025-02-01 00:00", "2025-02-02 12:00"): [],
        },
        threads={
            "thread-1": [header("one", "thread-1", "2024-12-20 10:00"), header("two", "thread-1", "2025-01-03 10:00")],
            "thread-2": [header("three", "thread-2", "2025-01-31 10:00")],
        },
    )

    result = asyncio.run(collected(client, "2025-02-02 12:00"))

    assert [item.thread_id for item in result] == ["thread-1", "thread-2"]
    assert [call for call in client.calls if call[0] == "messages"] == [
        ("messages", ("2024-12-17 12:00", "2025-01-01 00:00")),
        ("messages", ("2025-01-01 00:00", "2025-02-01 00:00")),
        ("messages", ("2025-02-01 00:00", "2025-02-02 12:00")),
    ]
    assert [call for call in client.calls if call[0] == "thread"] == [("thread", "thread-1"), ("thread", "thread-2")]


def test_empty_inbox_stops_after_provider_stats() -> None:
    client = FakeClient(oldest=None, inbox={}, threads={}, inbox_count=0)

    assert asyncio.run(collected(client, "2025-02-02 12:00")) == []
    assert client.calls == [("set_provider", "gmail"), ("stats", None)]


def test_empty_months_are_skipped_and_messages_outside_inbox_choose_target_month() -> None:
    client = FakeClient(
        oldest="2025-01-15 00:00",
        inbox={
            ("2025-01-15 00:00", "2025-02-01 00:00"): [header("inbox", "thread-1", "2025-01-20 10:00")],
            ("2025-02-01 00:00", "2025-03-01 00:00"): [],
            ("2025-03-01 00:00", "2025-03-02 12:00"): [],
        },
        threads={"thread-1": [header("inbox", "thread-1", "2025-01-20 10:00"), header("archive", "thread-1", "2025-02-04 10:00")]},
    )

    result = asyncio.run(collected(client, "2025-03-02 12:00"))

    assert [item.thread_id for item in result] == ["thread-1"]
    assert result[0].headers[-1].message_id == "archive"


def test_single_thread_is_deduplicated_and_no_body_or_attachment_capability_exists() -> None:
    client = FakeClient(
        oldest="2025-01-01 00:00",
        inbox={
            ("2025-01-01 00:00", "2025-02-01 00:00"): [header("one", "thread-1", "2025-01-01 01:00"), header("two", "thread-1", "2025-01-02 01:00")],
            ("2025-02-01 00:00", "2025-02-02 00:00"): [header("three", "thread-1", "2025-02-01 01:00")],
        },
        threads={"thread-1": [header("one", "thread-1", "2025-01-01 01:00"), header("three", "thread-1", "2025-02-01 01:00")]},
    )

    result = asyncio.run(collected(client, "2025-02-02 00:00"))

    assert [item.thread_id for item in result] == ["thread-1"]
    assert client.calls.count(("thread", "thread-1")) == 1
    assert {call[0] for call in client.calls} == {"set_provider", "stats", "messages", "thread"}


def test_skips_an_unreadable_thread_but_continues_the_month(caplog) -> None:
    client = FakeClient(
        oldest="2025-01-01 00:00",
        inbox={("2025-01-01 00:00", "2025-01-02 00:00"): [header("bad", "bad-thread", "2025-01-01 01:00"), header("good", "good-thread", "2025-01-01 02:00")]},
        threads={"bad-thread": RuntimeError("unreadable"), "good-thread": [header("good", "good-thread", "2025-01-01 02:00")]},
    )

    result = asyncio.run(collected(client, "2025-01-02 00:00"))

    assert [item.thread_id for item in result] == ["good-thread"]
    assert "bad-thread" in caplog.text


def test_month_query_error_is_not_misreported_as_an_empty_month() -> None:
    client = FakeClient(
        oldest="2025-01-01 00:00",
        inbox={("2025-01-01 00:00", "2025-01-02 00:00"): RuntimeError("mail unavailable")},
        threads={},
        inbox_count=1,
    )

    with pytest.raises(RuntimeError, match="mail unavailable"):
        asyncio.run(collected(client, "2025-01-02 00:00"))


def test_invalid_header_is_skipped_without_losing_other_threads() -> None:
    client = FakeClient(
        oldest="2025-01-01 00:00",
        inbox={("2025-01-01 00:00", "2025-01-02 00:00"): [{"message_id": "invalid"}, header("good", "good-thread", "2025-01-01 02:00")]},
        threads={"good-thread": [header("good", "good-thread", "2025-01-01 02:00")]},
    )

    result = asyncio.run(collected(client, "2025-01-02 00:00"))

    assert [item.thread_id for item in result] == ["good-thread"]


def test_uses_berlin_month_boundaries_for_a_dst_transition() -> None:
    client = FakeClient(
        oldest="2025-03-31 20:00",
        inbox={
            ("2025-03-31 20:00", "2025-03-31 22:00"): [],
            ("2025-03-31 22:00", "2025-04-02 10:00"): [
                header("one", "thread-1", "2025-03-31 22:30")
            ],
        },
        threads={"thread-1": [header("one", "thread-1", "2025-03-31 22:30")]},
    )
    collector = InboxThreadCollector(
        client,
        clock=lambda: datetime.fromisoformat(stamp("2025-04-02 10:00")),
    )

    result = asyncio.run(_collect(collector))

    assert [item.thread_id for item in result] == ["thread-1"]
    assert [call for call in client.calls if call[0] == "messages"] == [
        ("messages", ("2025-03-31 20:00", "2025-03-31 22:00")),
        ("messages", ("2025-03-31 22:00", "2025-04-02 10:00")),
    ]


async def _collect(collector: InboxThreadCollector) -> list:
    return [item async for item in collector.collect()]
