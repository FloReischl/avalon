"""AP5 confirmation and Gmail-label application for inbox-organizer threads."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from .client import ConfirmationCancelled
from .confirmation import ConfirmationTable
from .inbox_thread_collector import CollectedThread


logger = logging.getLogger(__name__)
DEFAULT_BATCH_SIZE = 100


class InboxConfirmationClient(Protocol):
    async def confirm(self, confirmation: ConfirmationTable) -> list[dict[str, object]]: ...
    async def get_mail_categories(self) -> list[str]: ...
    async def create_mail_categories(self, categories: list[str]) -> None: ...
    async def set_mail_categories(
        self, message_id: str, categories: list[str], *, archive: bool = False
    ) -> None: ...


@dataclass(frozen=True)
class ProposedThread:
    """Compact confirmation data; no mail body or attachment data is retained."""

    thread_id: str
    subject: str
    message_ids: tuple[str, ...]
    categories: tuple[str, ...]


@dataclass(frozen=True)
class BatchApplication:
    approved_threads: int
    unchanged_threads: int
    archived_threads: int
    failed_threads: int


def proposals_for_threads(
    threads: Iterable[CollectedThread], proposals: Mapping[str, list[str]]
) -> list[ProposedThread]:
    """Retain AP2 order and the IDs required to update every message in a thread."""
    result: list[ProposedThread] = []
    for thread in threads:
        categories = proposals.get(thread.thread_id)
        if not categories:
            continue
        message_ids = tuple(dict.fromkeys(header.message_id for header in thread.headers))
        if not message_ids:
            raise ValueError(f"Thread {thread.thread_id!r} has no message IDs.")
        newest = max(thread.headers, key=lambda header: header.internal_date)
        result.append(
            ProposedThread(
                thread_id=thread.thread_id,
                subject=newest.subject,
                message_ids=message_ids,
                categories=tuple(_deduplicate_categories(categories)),
            )
        )
    return result


def thread_batches(
    threads: Sequence[ProposedThread], *, size: int = DEFAULT_BATCH_SIZE
) -> list[list[ProposedThread]]:
    if size < 1:
        raise ValueError("Batch size must be positive.")
    return [list(threads[index : index + size]) for index in range(0, len(threads), size)]


def confirmation_table(batch: Sequence[ProposedThread], *, index: int, total: int) -> ConfirmationTable:
    if not batch:
        raise ValueError("Cannot build a confirmation for an empty batch.")
    table = (
        ConfirmationTable(f"Gmail Inbox Organizer – Batch {index} / {total}")
        .column("row_id", str, visible=False)
        .column("thread_id", str, label="Thread-ID")
        .column("subject", str, label="Betreff")
        .column("category", str, editable=True, label="Kategorie")
    )
    for thread in batch:
        for category_index, category in enumerate(thread.categories):
            table.rows.add(
                row_id=f"{thread.thread_id}:{category_index}",
                thread_id=thread.thread_id,
                subject=thread.subject,
                category=category,
            )
    return table


def approved_categories(
    batch: Sequence[ProposedThread], result: object
) -> dict[str, list[str]]:
    """Validate the returned table strictly before any Gmail mutation."""
    if not isinstance(result, list):
        raise ValueError("Confirmation returned invalid rows.")
    expected: dict[str, str] = {}
    for thread in batch:
        for index, _category in enumerate(thread.categories):
            expected[f"{thread.thread_id}:{index}"] = thread.thread_id

    seen: set[str] = set()
    approved: dict[str, list[str]] = {}
    for row in result:
        if not isinstance(row, Mapping):
            raise ValueError("Confirmation returned an invalid row.")
        row_id = row.get("row_id")
        decision = row.get("avalon_confirmation")
        category = row.get("category")
        if not isinstance(row_id, str) or row_id not in expected or row_id in seen:
            raise ValueError("Confirmation returned unknown or duplicate rows.")
        if decision not in {"approved", "rejected"}:
            raise ValueError("Confirmation returned an invalid decision.")
        if not isinstance(category, str):
            raise ValueError("Confirmation returned an invalid category.")
        seen.add(row_id)
        if decision == "approved":
            approved.setdefault(expected[row_id], []).append(_valid_category(category))
    if seen != set(expected):
        raise ValueError("Confirmation did not return every proposed row.")
    return {thread_id: _deduplicate_categories(categories) for thread_id, categories in approved.items()}


async def confirm_and_apply(
    client: InboxConfirmationClient,
    batch: Sequence[ProposedThread],
    *,
    index: int,
    total: int,
) -> BatchApplication | None:
    """Confirm one batch, create approved labels, then apply them per message.

    ``None`` represents an explicit user cancellation.  A successful Gmail call
    is deliberately never retried; labels and archive state share that call.
    """
    try:
        result = await client.confirm(confirmation_table(batch, index=index, total=total))
    except ConfirmationCancelled:
        return None
    approved = approved_categories(batch, result)
    unchanged = len(batch) - len(approved)
    if not approved:
        return BatchApplication(0, unchanged, 0, 0)

    existing = await client.get_mail_categories()
    if not isinstance(existing, list) or not all(isinstance(value, str) for value in existing):
        raise ValueError("Mail capability returned invalid categories.")
    required = _deduplicate_categories(
        category for categories in approved.values() for category in categories
    )
    existing_names = {value.strip() for value in existing}
    missing = [category for category in required if category not in existing_names]
    if missing:
        await client.create_mail_categories(missing)

    by_id = {thread.thread_id: thread for thread in batch}
    archived = failed = 0
    for thread_id, categories in approved.items():
        thread = by_id[thread_id]
        try:
            for message_id in thread.message_ids:
                await client.set_mail_categories(message_id, categories, archive=True)
        except Exception:
            failed += 1
            logger.exception("Skipping Gmail thread %s after category update failure.", thread_id)
        else:
            archived += 1
    return BatchApplication(len(approved), unchanged, archived, failed)


def _deduplicate_categories(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for category in values:
        value = _valid_category(category)
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _valid_category(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Category must be text.")
    category = value.strip()
    if (
        not category
        or any(ord(character) < 32 for character in category)
        or any(not segment.strip() for segment in category.split("/"))
        or _is_system_category(category)
    ):
        raise ValueError("Confirmation contains an invalid category.")
    return category


def _is_system_category(value: str) -> bool:
    return value.upper() in {
        "INBOX", "SENT", "DRAFT", "DRAFTS", "SPAM", "TRASH", "STARRED", "IMPORTANT", "ALL MAIL"
    } or value.startswith(("[Gmail]/", "[Google Mail]/"))
