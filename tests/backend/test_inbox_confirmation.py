"""Offline AP5 contracts for Gmail inbox-organizer confirmation and application."""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "workflows"))

from avalon_workflows.client import ConfirmationCancelled
from avalon_workflows.inbox_confirmation import (
    ProposedThread,
    approved_categories,
    confirm_and_apply,
    confirmation_table,
    thread_batches,
)
from avalon_workflows.inbox_thread_collector import CollectedThread, MailHeader


def thread(identifier: str, *categories: str) -> ProposedThread:
    return ProposedThread(
        thread_id=identifier,
        subject=f"Subject {identifier}",
        message_ids=(f"{identifier}-old", f"{identifier}-new"),
        categories=tuple(categories),
    )


def approved(table) -> list[dict[str, object]]:
    return [
        {**row, "avalon_confirmation": "approved"}
        for row in table.to_dict()["rows"]
    ]


class Client:
    def __init__(
        self,
        result,
        *,
        existing=(),
        fail_message: str | None = None,
        create_error: Exception | None = None,
    ) -> None:
        self.result = result
        self.existing = list(existing)
        self.fail_message = fail_message
        self.create_error = create_error
        self.created: list[list[str]] = []
        self.set_calls: list[tuple[str, list[str], bool]] = []

    async def confirm(self, table):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result(table)

    async def get_mail_categories(self):
        return self.existing

    async def create_mail_categories(self, categories):
        self.created.append(categories)
        if self.create_error is not None:
            raise self.create_error

    async def set_mail_categories(self, message_id, categories, *, archive=False):
        self.set_calls.append((message_id, categories, archive))
        if message_id == self.fail_message:
            raise RuntimeError("Gmail unavailable")


def test_batches_are_by_thread_and_keep_every_category_together() -> None:
    threads = [thread(str(index), "Year/2026", "Finance") for index in range(101)]

    batches = thread_batches(threads)

    assert [len(batch) for batch in batches] == [100, 1]
    assert [item.thread_id for item in batches[0]][-1] == "99"
    assert batches[1][0].categories == ("Year/2026", "Finance")


def test_confirmation_has_one_stable_row_per_thread_category_and_editable_category() -> None:
    table = confirmation_table([thread("123", "Jahr/2026", "has-attachments")], index=1, total=1)
    payload = table.to_dict()

    assert payload["rows"] == [
        {"row_id": "123:0", "thread_id": "123", "subject": "Subject 123", "category": "Jahr/2026"},
        {"row_id": "123:1", "thread_id": "123", "subject": "Subject 123", "category": "has-attachments"},
    ]
    assert next(column for column in payload["schema"]["columns"] if column["key"] == "category")["editable"] is True


def test_approved_categories_uses_edited_values_and_drops_rejected_rows() -> None:
    batch = [thread("123", "Old", "has-attachments")]
    result = [
        {"row_id": "123:0", "category": "Finanzen/Rechnungen", "avalon_confirmation": "approved"},
        {"row_id": "123:1", "category": "has-attachments", "avalon_confirmation": "rejected"},
    ]

    assert approved_categories(batch, result) == {"123": ["Finanzen/Rechnungen"]}


def test_invalid_edited_category_rejects_the_entire_confirmation_result() -> None:
    with pytest.raises(ValueError, match="invalid category"):
        approved_categories(
            [thread("123", "Safe")],
            [{"row_id": "123:0", "category": "INBOX", "avalon_confirmation": "approved"}],
        )


def test_missing_confirmation_row_is_rejected_before_any_mail_mutation() -> None:
    with pytest.raises(ValueError, match="did not return every"):
        approved_categories(
            [thread("123", "Finance", "Travel")],
            [{"row_id": "123:0", "category": "Finance", "avalon_confirmation": "approved"}],
        )


def test_only_approved_categories_are_created_and_all_thread_messages_are_archived() -> None:
    batch = [thread("123", "Finanzen/Rechnungen", "has-attachments"), thread("456", "Reisen")]
    client = Client(
        lambda table: [
            {**row, "avalon_confirmation": "approved" if row["thread_id"] == "123" else "rejected"}
            for row in table.to_dict()["rows"]
        ],
        existing=["has-attachments"],
    )

    outcome = asyncio.run(confirm_and_apply(client, batch, index=1, total=1))

    assert outcome is not None
    assert outcome.archived_threads == 1
    assert outcome.unchanged_threads == 1
    assert client.created == [["Finanzen/Rechnungen"]]
    assert client.set_calls == [
        ("123-old", ["Finanzen/Rechnungen", "has-attachments"], True),
        ("123-new", ["Finanzen/Rechnungen", "has-attachments"], True),
    ]


def test_message_error_skips_only_that_thread_without_a_second_archive_attempt() -> None:
    batch = [thread("bad", "Finance"), thread("good", "Travel")]
    client = Client(approved, fail_message="bad-old")

    outcome = asyncio.run(confirm_and_apply(client, batch, index=1, total=1))

    assert outcome is not None
    assert outcome.archived_threads == 1
    assert outcome.failed_threads == 1
    assert client.set_calls == [
        ("bad-old", ["Finance"], True),
        ("good-old", ["Travel"], True),
        ("good-new", ["Travel"], True),
    ]


def test_create_category_failure_prevents_all_application_in_the_batch() -> None:
    client = Client(approved, create_error=RuntimeError("label creation failed"))

    with pytest.raises(RuntimeError, match="label creation failed"):
        asyncio.run(confirm_and_apply(client, [thread("123", "Finance")], index=1, total=1))

    assert client.created == [["Finance"]]
    assert client.set_calls == []


def test_cancel_leaves_the_open_batch_unchanged() -> None:
    client = Client(ConfirmationCancelled())

    assert asyncio.run(confirm_and_apply(client, [thread("123", "Finance")], index=1, total=1)) is None
    assert client.created == []
    assert client.set_calls == []
