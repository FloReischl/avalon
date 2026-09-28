"""Tests for the Avalon persistence foundation."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.persistence.database import (
    create_database_engine,
    database_url,
    database_path,
)
from app.persistence.migrations import migration_script_location, run_migrations


def test_database_path_is_per_user(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    assert database_path() == tmp_path / ".avalon" / "avalon.sqlite"


def test_migrations_create_initial_schema(tmp_path: Path) -> None:
    path = tmp_path / ".avalon" / "avalon.sqlite"

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
        assert {"seq"}.issubset(
            {column["name"] for column in inspector.get_columns("messages")}
        )
        assert {
            "compressed_context",
            "compressed_through_seq",
            "compression_version",
            "compression_error_code",
            "next_message_seq",
        }.issubset({column["name"] for column in inspector.get_columns("chats")})
    finally:
        engine.dispose()


def test_migrations_are_idempotent(tmp_path: Path) -> None:
    path = tmp_path / ".avalon" / "avalon.sqlite"

    run_migrations(path)
    run_migrations(path)

    engine = create_database_engine(path)
    try:
        with engine.connect() as connection:
            new_revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()

        assert new_revision != None
    finally:
        engine.dispose()


def test_authorization_migration_marks_existing_permissions_active(tmp_path: Path) -> None:
    path = tmp_path / "avalon.sqlite"
    config = Config()
    config.set_main_option("script_location", str(migration_script_location()))
    config.set_main_option("sqlalchemy.url", database_url(path))
    command.upgrade(config, "0005")
    engine = create_database_engine(path)
    try:
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO permission_catalog (id, context, key) VALUES (1, 'web', 'search')"))
            connection.execute(text("INSERT INTO principal_permissions (principal_id, permission_catalog_id, scope, validity_type, default_expiry) VALUES (1, 1, '[]', 'duration', 1)"))
            connection.execute(text("INSERT INTO permission_grants (principal_permission_id, valid_from, valid_to, range) VALUES (1, '2026-01-01', '2026-01-02', NULL)"))
    finally:
        engine.dispose()

    run_migrations(path)
    engine = create_database_engine(path)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT is_active FROM principal_permissions")).scalar_one() == 1
            assert connection.execute(text("SELECT principal_permission_id FROM permission_grants")).scalar_one() == 1
    finally:
        engine.dispose()


def test_authorization_migration_downgrade_removes_active_column(tmp_path: Path) -> None:
    path = tmp_path / "avalon.sqlite"
    run_migrations(path)
    config = Config()
    config.set_main_option("script_location", str(migration_script_location()))
    config.set_main_option("sqlalchemy.url", database_url(path))
    command.downgrade(config, "0005")

    engine = create_database_engine(path)
    try:
        assert "is_active" not in {
            column["name"]
            for column in inspect(engine).get_columns("principal_permissions")
        }
    finally:
        engine.dispose()


def test_sqlite_foreign_keys_are_enabled(tmp_path: Path) -> None:
    engine = create_database_engine(tmp_path / "avalon.sqlite")
    try:
        with engine.connect() as connection:
            enabled = connection.execute(
                text("PRAGMA foreign_keys")
            ).scalar_one()

        assert enabled == 1
    finally:
        engine.dispose()


def test_compression_migration_backfills_existing_message_sequences(
    tmp_path: Path,
) -> None:
    path = tmp_path / "avalon.sqlite"
    config = Config()
    config.set_main_option("script_location", str(migration_script_location()))
    config.set_main_option("sqlalchemy.url", database_url(path))
    command.upgrade(config, "0003")

    engine = create_database_engine(path)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO chats (id, title) VALUES (1, 'Chat')")
            )
            connection.execute(
                text(
                    "INSERT INTO messages (id, chat_id, role, content, created_at) "
                    "VALUES (2, 1, 'assistant', 'Zweite', '2026-01-01 10:00:00')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO messages (id, chat_id, role, content, created_at) "
                    "VALUES (1, 1, 'user', 'Erste', '2026-01-01 10:00:00')"
                )
            )
    finally:
        engine.dispose()

    run_migrations(path)
    engine = create_database_engine(path)
    try:
        with engine.connect() as connection:
            sequences = connection.execute(
                text("SELECT id, seq FROM messages ORDER BY id")
            ).all()
            next_sequence = connection.execute(
                text("SELECT next_message_seq FROM chats WHERE id = 1")
            ).scalar_one()

        assert sequences == [(1, 1), (2, 2)]
        assert next_sequence == 3
    finally:
        engine.dispose()
