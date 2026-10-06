"""Persistence-level coverage for agent-owned proactive permissions."""

from datetime import datetime, timedelta

from sqlalchemy import select

from app.api.routes.chats import _proactive_permissions
from app.persistence.authorization_repository import AuthorizationRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.persistence.migrations import run_migrations
from app.persistence.models import Agent, Chat, PermissionCatalog, PermissionGrant, PermissionSet


def build_repository(tmp_path):
    path = tmp_path / "avalon.sqlite"
    run_migrations(path)
    engine = create_database_engine(path)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        default = session.scalar(select(Agent).where(Agent.key == "default"))
        assert default is not None
        podcast = Agent(key="podcast", name="Podcast")
        session.add(podcast)
        session.flush()
        session.add_all([
            Chat(id=1, title="Default", agent_id=default.id),
            Chat(id=2, title="Podcast", agent_id=podcast.id),
        ])
        catalog = PermissionCatalog(context="web", key="search")
        session.add(catalog)
        session.flush()
        duration = PermissionSet(agent_id=default.id, permission_catalog_id=catalog.id, scope="[]", validity_type="duration", default_expiry=3600)
        permanent = PermissionSet(agent_id=default.id, permission_catalog_id=catalog.id, scope='["permanent"]', validity_type="permanent", default_expiry=0)
        range_set = PermissionSet(agent_id=podcast.id, permission_catalog_id=catalog.id, scope='["range"]', validity_type="range", default_expiry=3600)
        session.add_all([duration, permanent, range_set])
        session.flush()
        now = datetime.now()
        session.add(PermissionGrant(permission_set_id=range_set.id, valid_from=now - timedelta(minutes=1), valid_to=now + timedelta(minutes=1), range='["x"]'))
    return AuthorizationRepository(factory), engine, duration.id, permanent.id, range_set.id


def test_proactive_permissions_are_owned_by_the_chat_agent(tmp_path) -> None:
    repository, engine, duration_id, permanent_id, range_id = build_repository(tmp_path)
    try:
        assert {item.id for item in _proactive_permissions(1, repository)} == {duration_id, permanent_id}
        permissions = _proactive_permissions(2, repository)
        assert [item.id for item in permissions] == [range_id]
        assert permissions[0].read_only is True
    finally:
        engine.dispose()


def test_proactive_duration_grant_can_be_created_and_revoked(tmp_path) -> None:
    repository, engine, duration_id, _, _ = build_repository(tmp_path)
    try:
        now = datetime.now()
        repository.save_proactive_grant(duration_id, "duration", now + timedelta(hours=1), now)
        assert repository.get_active_grant(duration_id, now) is not None
        repository.revoke_proactive_grant(duration_id, now)
        assert repository.get_active_grant(duration_id, now) is None
    finally:
        engine.dispose()
