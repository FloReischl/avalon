"""Tests for the Avalo persistence foundation."""

from pathlib import Path

from sqlalchemy import inspect, text

from app.persistence.database import (
    create_database_engine,
    database_path,
)
from app.persistence.migrations import run_migrations


def test_database_path_is_per_user(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    assert database_path() == tmp_path / ".avalo" / "avalo.sqlite"


def test_migrations_create_initial_schema(tmp_path: Path) -> None:
    path = tmp_path / ".avalo" / "avalo.sqlite"

    run_migrations(path)

    assert path.is_file()

    engine = create_database_engine(path)
    try:
        inspector = inspect(engine)
        assert set(inspector.get_table_names()) >= {
            "alembic_version",
            "chats",
            "messages",
        }

        message_foreign_keys = inspector.get_foreign_keys("messages")
        assert len(message_foreign_keys) == 1
        assert message_foreign_keys[0]["referred_table"] == "chats"
        assert message_foreign_keys[0]["options"]["ondelete"] == "CASCADE"
    finally:
        engine.dispose()


def test_migrations_are_idempotent(tmp_path: Path) -> None:
    path = tmp_path / ".avalo" / "avalo.sqlite"

    run_migrations(path)
    run_migrations(path)

    engine = create_database_engine(path)
    try:
        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()

        assert revision == "0001"
    finally:
        engine.dispose()


def test_sqlite_foreign_keys_are_enabled(tmp_path: Path) -> None:
    engine = create_database_engine(tmp_path / "avalo.sqlite")
    try:
        with engine.connect() as connection:
            enabled = connection.execute(
                text("PRAGMA foreign_keys")
            ).scalar_one()

        assert enabled == 1
    finally:
        engine.dispose()