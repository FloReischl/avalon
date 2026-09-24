"""Alembic migration bootstrap for the local Avalon database."""

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.persistence.database import database_path, database_url


def migration_script_location() -> Path:
    """Return the repository migration directory."""
    return Path(__file__).resolve().parents[3] / "alembic"


def run_migrations(path: Path | None = None) -> None:
    """Upgrade the Avalon database to the current schema revision."""
    target = path or database_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    config = Config()
    config.set_main_option("script_location", str(migration_script_location()))
    config.set_main_option("sqlalchemy.url", database_url(target))
    command.upgrade(config, "head")