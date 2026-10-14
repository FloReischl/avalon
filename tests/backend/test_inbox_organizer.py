"""Offline data-flow contract connecting AP2, AP3, and AP4."""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "workflows"))

from avalon_workflows.inbox_organizer import InboxOrganizer
from avalon_workflows.inbox_thread_collector import CollectedThread, MailHeader


class Collector:
    def collect(self):
        async def values():
            yield "thread"

        return values()


class Analyzer:
    async def analyze(self, threads):
        assert [thread async for thread in threads] == ["thread"]
        return {"thread": ["Rechnung"]}


class Normalizer:
    async def normalize(self, proposals):
        assert proposals == {"thread": ["Rechnung"]}
        return {"thread": ["Finanzen/Rechnungen"]}


def test_organizer_hands_ap3_proposals_to_ap4_before_the_future_ap5() -> None:
    organizer = InboxOrganizer(Collector(), Analyzer(), Normalizer())

    assert asyncio.run(organizer.analyze()) == {
        "thread": ["Finanzen/Rechnungen"]
    }


def _thread(identifier: str) -> CollectedThread:
    return CollectedThread(
        identifier,
        (
            MailHeader(
                message_id=f"message-{identifier}",
                thread_id=identifier,
                internal_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                subject=f"Subject {identifier}",
                sender="sender@example.test",
                is_read=True,
            ),
        ),
    )


def test_full_pipeline_confirms_and_archives_each_analyzed_thread() -> None:
    class PipelineCollector:
        def collect(self):
            async def values():
                yield _thread("one")
                yield _thread("two")
            return values()

    class PipelineAnalyzer:
        async def analyze(self, threads):
            return {item.thread_id: ["Finance"] async for item in threads}

    class PipelineNormalizer:
        async def normalize(self, proposals):
            return proposals

    class Client:
        def __init__(self) -> None:
            self.progress_messages = []
            self.set_calls = []

        async def progress(self, message): self.progress_messages.append(message)
        async def confirm(self, table):
            return [{**row, "avalon_confirmation": "approved"} for row in table.to_dict()["rows"]]
        async def get_mail_categories(self): return []
        async def create_mail_categories(self, _categories): return None
        async def set_mail_categories(self, message_id, categories, *, archive=False):
            self.set_calls.append((message_id, categories, archive))

    client = Client()
    result = asyncio.run(InboxOrganizer(
        PipelineCollector(), PipelineAnalyzer(), PipelineNormalizer(), client=client
    ).run())

    assert result == {
        "collected_threads": 2,
        "analyzed_threads": 2,
        "archived_threads": 2,
        "unchanged_threads": 0,
        "failed_threads": 0,
        "cancelled": False,
    }
    assert client.set_calls == [
        ("message-one", ["Finance"], True),
        ("message-two", ["Finance"], True),
    ]
    assert any("Abschluss: 2 erfasst" in message for message in client.progress_messages)


def test_later_batch_cancel_preserves_completed_batches_and_counts_all_analyzed_threads() -> None:
    class PipelineCollector:
        def collect(self):
            async def values():
                yield _thread("one")
                yield _thread("two")
            return values()

    class PipelineAnalyzer:
        async def analyze(self, threads):
            return {item.thread_id: ["Nicht kategorisiert"] async for item in threads}

    class PipelineNormalizer:
        async def normalize(self, proposals): return proposals

    class Client:
        def __init__(self) -> None:
            self.confirmations = 0
            self.set_calls = []

        async def progress(self, _message): return None
        async def confirm(self, table):
            self.confirmations += 1
            if self.confirmations == 2:
                from avalon_workflows.client import ConfirmationCancelled
                raise ConfirmationCancelled()
            return [{**row, "avalon_confirmation": "approved"} for row in table.to_dict()["rows"]]
        async def get_mail_categories(self): return []
        async def create_mail_categories(self, _categories): return None
        async def set_mail_categories(self, message_id, categories, *, archive=False):
            self.set_calls.append((message_id, categories, archive))

    client = Client()
    result = asyncio.run(InboxOrganizer(
        PipelineCollector(), PipelineAnalyzer(), PipelineNormalizer(), client=client, batch_size=1
    ).run())

    assert result == {
        "collected_threads": 2,
        "analyzed_threads": 2,
        "archived_threads": 1,
        "unchanged_threads": 1,
        "failed_threads": 0,
        "cancelled": True,
    }
    assert client.set_calls == [("message-one", ["Nicht kategorisiert"], True)]
