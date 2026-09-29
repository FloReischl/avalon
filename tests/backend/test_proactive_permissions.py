"""Persistence-level coverage for direct chat permission management."""

from datetime import datetime, timedelta

from sqlalchemy import select, text, update

from app.api.routes.chats import _proactive_permissions
from app.persistence.authorization_repository import AuthorizationRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.persistence.migrations import run_migrations
from app.persistence.models import Agent, Chat, PermissionCatalog, PermissionGrant, Principal, PrincipalPermission


def build_repository(tmp_path):
    path = tmp_path / "avalon.sqlite"
    run_migrations(path)
    engine = create_database_engine(path)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        direct_principal = Principal(key="direct")
        agent_principal = Principal(key="agent:one")
        session.add_all([direct_principal, agent_principal])
        session.flush()
        default_principal = session.scalar(
            select(Principal).where(Principal.key == "chat-default")
        )
        assert default_principal is not None
        agent = Agent(key="one", principal_id=agent_principal.id)
        session.add(agent)
        session.flush()
        direct_chat = Chat(id=1, title="Direct", principal_id=direct_principal.id)
        agent_chat = Chat(id=2, title="Agent", agent_id=agent.id)
        default_chat = Chat(id=3, title="Default", principal_id=default_principal.id)
        session.add_all([direct_chat, agent_chat, default_chat])
        catalog = PermissionCatalog(context="web", key="search")
        session.add(catalog)
        session.flush()
        duration = PrincipalPermission(principal_id=direct_principal.id, permission_catalog_id=catalog.id, scope="[]", validity_type="duration", default_expiry=3600)
        default_duration = PrincipalPermission(principal_id=default_principal.id, permission_catalog_id=catalog.id, scope="[]", validity_type="duration", default_expiry=3600)
        permanent = PrincipalPermission(principal_id=direct_principal.id, permission_catalog_id=catalog.id, scope='["permanent"]', validity_type="permanent", default_expiry=0)
        range_permission = PrincipalPermission(principal_id=direct_principal.id, permission_catalog_id=catalog.id, scope='["range"]', validity_type="range", default_expiry=3600)
        session.add_all([duration, default_duration, permanent, range_permission])
        session.flush()
        now = datetime.now()
        session.add(PermissionGrant(principal_permission_id=range_permission.id, valid_from=now - timedelta(minutes=1), valid_to=now + timedelta(minutes=1), range='["x"]'))
        # Simulate a pre-principal legacy chat without weakening the current DB invariant.
        session.execute(text("PRAGMA ignore_check_constraints = ON"))
        session.execute(update(Chat).where(Chat.id == default_chat.id).values(principal_id=None))
    return AuthorizationRepository(factory), engine, duration.id, default_duration.id, permanent.id, range_permission.id


def test_proactive_permissions_resolve_chat_principal_and_apply_range_visibility(tmp_path) -> None:
    repository, engine, duration_id, _, permanent_id, range_id = build_repository(tmp_path)
    try:
        assert repository.get_effective_principal_id_for_chat(1) is not None
        assert repository.get_effective_principal_id_for_chat(2) is not None
        permissions = _proactive_permissions(1, repository)
        assert {permission.id for permission in permissions} == {duration_id, permanent_id, range_id}
        duration = next(permission for permission in permissions if permission.id == duration_id)
        assert duration.grant is None
        assert duration.default_expiry == 3600
        range_permission = next(permission for permission in permissions if permission.id == range_id)
        assert range_permission.read_only is True
    finally:
        engine.dispose()


def test_proactive_duration_creates_updates_and_expires_grants(tmp_path) -> None:
    repository, engine, duration_id, _, _, _ = build_repository(tmp_path)
    try:
        now = datetime.now()
        created = repository.save_proactive_grant(duration_id, "duration", now + timedelta(hours=1), now)
        assert repository.get_active_grant(duration_id, now) is not None
        extended = repository.save_proactive_grant(duration_id, "duration", now + timedelta(hours=2), now)
        assert extended.id == created.id
        shortened = repository.save_proactive_grant(duration_id, "duration", now + timedelta(minutes=1), now)
        assert shortened.valid_to == now + timedelta(minutes=1)
        repository.save_proactive_grant(duration_id, "duration", now, now)
        assert repository.get_active_grant(duration_id, now) is None
    finally:
        engine.dispose()


def test_proactive_permanent_grant_is_created_and_reused(tmp_path) -> None:
    repository, engine, _, _, permanent_id, _ = build_repository(tmp_path)
    try:
        now = datetime.now()
        created = repository.save_proactive_grant(permanent_id, "permanent", None, now)
        reused = repository.save_proactive_grant(permanent_id, "permanent", None, now)
        assert reused.id == created.id
        assert created.valid_to.year == 2040
    finally:
        engine.dispose()


def test_proactive_permissions_for_normal_chat_use_default_principal(tmp_path) -> None:
    repository, engine, _, default_permission_id, _, _ = build_repository(tmp_path)
    try:
        assert repository.get_effective_principal_id_for_chat(3) is not None
        permissions = _proactive_permissions(3, repository)
        assert [permission.id for permission in permissions] == [default_permission_id]
    finally:
        engine.dispose()
