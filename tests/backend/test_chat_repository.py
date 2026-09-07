"""Tests for persistent chat repository operations."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.persistence.chat_repository import ChatRepository
from app.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from app.persistence.migrations import run_migrations
from app.persistence.models import Chat, Message


@pytest.fixture
def repository(tmp_path: Path):
    """Provide a repository backed by a migrated temporary database."""
    path = tmp_path / "avalo.sqlite"
    run_migrations(path)

    engine = create_database_engine(path)
    session_factory = create_session_factory(engine)

    try:
        yield ChatRepository(session_factory), session_factory
    finally:
        engine.dispose()


def test_create_and_get_chat(repository) -> None:
    repo, _ = repository

    created = repo.create_chat("New 2026-09-07 12:00:00")
    loaded = repo.get_chat(created.id)

    assert loaded is not None
    assert loaded.id == created.id
    assert loaded.title == "New 2026-09-07 12:00:00"
    assert loaded.title_is_manual is False


def test_create_chat_normalizes_title(repository) -> None:
    repo, _ = repository

    chat = repo.create_chat("  New Chat  ")

    assert chat.title == "New Chat"


@pytest.mark.parametrize("title", ["", " ", "\n\t"])
def test_create_chat_rejects_empty_title(repository, title: str) -> None:
    repo, _ = repository

    with pytest.raises(ValueError):
        repo.create_chat(title)


def test_create_chat_rejects_title_over_200_characters(repository) -> None:
    repo, _ = repository

    with pytest.raises(ValueError):
        repo.create_chat("x" * 201)


def test_create_chat_with_message_is_atomic(repository) -> None:
    repo, _ = repository

    chat = repo.create_chat_with_message(
        "New 2026-09-07 12:00:00",
        "user",
        "Hallo",
    )

    messages = repo.get_messages(chat.id)

    assert len(messages) == 1
    assert messages[0].role == "user"
    assert messages[0].content == "Hallo"


def test_create_chat_with_message_rejects_invalid_message(repository) -> None:
    repo, session_factory = repository

    with pytest.raises(ValueError):
        repo.create_chat_with_message("New Chat", "system", "Hallo")

    with session_factory() as session:
        chat_count = session.scalar(
            select(func.count()).select_from(Chat)
        )

    assert chat_count == 0


def test_add_and_get_messages_in_chronological_order(repository) -> None:
    repo, _ = repository
    chat = repo.create_chat("Chat")

    first = repo.add_message(chat.id, "user", "Hallo")
    second = repo.add_message(chat.id, "assistant", "Hallo Flo")

    messages = repo.get_messages(chat.id)

    assert [message.id for message in messages] == [first.id, second.id]
    assert [message.role for message in messages] == ["user", "assistant"]
    assert [message.content for message in messages] == ["Hallo", "Hallo Flo"]


@pytest.mark.parametrize("role", ["system", "tool", "", "USER"])
def test_add_message_rejects_invalid_role(repository, role: str) -> None:
    repo, _ = repository
    chat = repo.create_chat("Chat")

    with pytest.raises(ValueError):
        repo.add_message(chat.id, role, "Hallo")


def test_add_message_rejects_empty_content(repository) -> None:
    repo, _ = repository
    chat = repo.create_chat("Chat")

    with pytest.raises(ValueError):
        repo.add_message(chat.id, "user", "")


def test_context_returns_only_latest_messages_in_chronological_order(
    repository,
) -> None:
    repo, _ = repository
    chat = repo.create_chat("Chat")

    for index in range(105):
        repo.add_message(chat.id, "user", f"Message {index}")

    messages = repo.get_context_messages(chat.id)

    assert len(messages) == 100
    assert messages[0].content == "Message 5"
    assert messages[-1].content == "Message 104"


def test_context_supports_explicit_limit(repository) -> None:
    repo, _ = repository
    chat = repo.create_chat("Chat")

    for index in range(5):
        repo.add_message(chat.id, "user", f"Message {index}")

    messages = repo.get_context_messages(chat.id, limit=2)

    assert [message.content for message in messages] == [
        "Message 3",
        "Message 4",
    ]


def test_context_rejects_non_positive_limit(repository) -> None:
    repo, _ = repository
    chat = repo.create_chat("Chat")

    with pytest.raises(ValueError):
        repo.get_context_messages(chat.id, limit=0)


def test_list_chats_orders_by_latest_message_activity(repository) -> None:
    repo, session_factory = repository
    older_chat = repo.create_chat("Older")
    newer_chat = repo.create_chat("Newer")

    older_message = repo.add_message(older_chat.id, "user", "Older message")
    newer_message = repo.add_message(newer_chat.id, "user", "Newer message")

    base_time = datetime(2026, 9, 7, 10, 0, 0)
    with session_factory() as session:
        session.get(Message, older_message.id).created_at = base_time
        session.get(Message, newer_message.id).created_at = (
            base_time + timedelta(minutes=1)
        )
        session.commit()

    chats = repo.list_chats()

    assert [chat.id for chat in chats] == [newer_chat.id, older_chat.id]


def test_rename_chat_normalizes_title_and_marks_it_manual(repository) -> None:
    repo, _ = repository
    chat = repo.create_chat("Original")

    renamed = repo.rename_chat(chat.id, "  Mein Chat  ")

    assert renamed is not None
    assert renamed.title == "Mein Chat"
    assert renamed.title_is_manual is True


@pytest.mark.parametrize("title", ["", " ", "\n\t"])
def test_rename_chat_rejects_empty_title(repository, title: str) -> None:
    repo, _ = repository
    chat = repo.create_chat("Original")

    with pytest.raises(ValueError):
        repo.rename_chat(chat.id, title)


def test_rename_chat_rejects_title_over_200_characters(repository) -> None:
    repo, _ = repository
    chat = repo.create_chat("Original")

    with pytest.raises(ValueError):
        repo.rename_chat(chat.id, "x" * 201)


def test_rename_unknown_chat_returns_none(repository) -> None:
    repo, _ = repository

    assert repo.rename_chat(999, "Title") is None


def test_delete_chat_physically_removes_chat_and_messages(repository) -> None:
    repo, session_factory = repository
    chat = repo.create_chat("Chat")
    repo.add_message(chat.id, "user", "Hallo")
    repo.add_message(chat.id, "assistant", "Hallo Flo")

    assert repo.delete_chat(chat.id) is True
    assert repo.get_chat(chat.id) is None

    with session_factory() as session:
        message_count = session.scalar(
            select(func.count())
            .select_from(Message)
            .where(Message.chat_id == chat.id)
        )

    assert message_count == 0


def test_delete_unknown_chat_returns_false(repository) -> None:
    repo, _ = repository

    assert repo.delete_chat(999) is False


def test_list_chats_excludes_unpersisted_empty_chat_concept(repository) -> None:
    repo, session_factory = repository
    chat = repo.create_chat("Empty")

    assert repo.list_chats() == []

    with session_factory() as session:
        persisted = session.get(Chat, chat.id)

    assert persisted is not None