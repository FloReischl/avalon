"""Migration coverage for the generalized conversation model."""

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.persistence.database import create_database_engine, database_url
from app.persistence.migrations import migration_script_location


def test_0009_ports_text_history_and_discards_workflow_placeholders(tmp_path) -> None:
    database = tmp_path / "avalon.sqlite"
    config = Config()
    config.set_main_option("script_location", str(migration_script_location()))
    config.set_main_option("sqlalchemy.url", database_url(database))
    command.upgrade(config, "0008")

    engine = create_database_engine(database)
    try:
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO chats (id, principal_id, title, next_message_seq) VALUES (1, 1, 'History', 3)"))
            connection.execute(text("INSERT INTO messages (id, chat_id, role, content, seq) VALUES (1, 1, 'user', 'Hallo', 1), (2, 1, 'assistant', 'Hi', 2)"))
            connection.execute(text("INSERT INTO workflow_executions (id, message_id, state, runtime_token_hash) VALUES (1, 2, 'running', 'hash')"))
    finally:
        engine.dispose()

    command.upgrade(config, "head")
    engine = create_database_engine(database)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM text_messages")).scalar_one() == 2
            assert connection.execute(text("SELECT content FROM text_messages WHERE message_id = 1")).scalar_one() == "Hallo"
            assert connection.execute(text("SELECT count(*) FROM workflow_executions")).scalar_one() == 0
    finally:
        engine.dispose()
