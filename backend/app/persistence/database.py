"""SQLite database configuration and session lifecycle."""

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def database_path() -> Path:
    """Return the per-user Avalon SQLite database path."""
    return Path.home() / ".avalon" / "avalon.sqlite"


def database_url(path: Path | None = None) -> str:
    """Return a SQLAlchemy URL for the Avalon SQLite database."""
    target = path or database_path()
    return f"sqlite:///{target}"


def create_database_engine(path: Path | None = None) -> Engine:
    """Create an Avalon SQLite engine and enable foreign-key enforcement."""
    target = path or database_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(database_url(target))

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
        del connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create sessions bound to one Avalon database engine."""
    return sessionmaker(bind=engine, expire_on_commit=False)


def session_scope(engine: Engine) -> Iterator[Session]:
    """Yield one session and always close it afterwards."""
    session = create_session_factory(engine)()
    try:
        yield session
    finally:
        session.close()