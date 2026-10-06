"""Chat permission ownership is delegated to the chat's configured agent."""

from pathlib import Path

import pytest

from app.persistence.authorization_repository import AuthorizationRepository
from app.persistence.chat_repository import ChatRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.persistence.migrations import run_migrations
from app.persistence.models import Agent


@pytest.fixture
def repositories(tmp_path: Path):
    path = tmp_path / "avalon.sqlite"
    run_migrations(path)
    engine = create_database_engine(path)
    factory = create_session_factory(engine)
    try:
        yield AuthorizationRepository(factory), ChatRepository(factory)
    finally:
        engine.dispose()


def test_chat_authorization_uses_its_default_agent(repositories) -> None:
    authorization, chats = repositories
    chat = chats.create_chat("Chat")

    assert authorization.get_agent_id_for_chat(chat.id) == chat.agent_id


def test_unload_agent_restores_the_default_agent(repositories) -> None:
    _, chats = repositories
    with chats.session_factory.begin() as session:
        session.add(Agent(key="podcast", name="Podcast"))
    podcast = chats.get_agent_by_key("podcast")
    assert podcast is not None
    chat = chats.create_chat("Chat", podcast.id)

    assert chats.unload_agent(chat.id) is True
    restored = chats.get_chat(chat.id)
    assert restored is not None
    assert restored.agent.key == "default"
