from pathlib import Path

import pytest
from sqlalchemy import select

from app.agents_config import AgentsConfig
from app.persistence.authorization_repository import AuthorizationRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.persistence.migrations import run_migrations
from app.persistence.models import Agent, PermissionCatalog, PermissionSet


def _config(permissions: list[dict]) -> AgentsConfig:
    return AgentsConfig.model_validate(
        {"agents": [{"name": "Hedwig", "key": "podcast", "persona": "P", "instructions": "I", "permissions": permissions}]}
    )


def _permission(context="web", key="search", scope=None, expiry=7200) -> dict:
    return {
        "permission_catalog": {"context": context, "key": key},
        "permission_set": {
            "scope": [] if scope is None else scope,
            "validity_type": "duration",
            "default_expiry": expiry,
        },
    }


@pytest.fixture
def repository(tmp_path: Path):
    path = tmp_path / "avalon.sqlite"
    run_migrations(path)
    engine = create_database_engine(path)
    try:
        yield AuthorizationRepository(create_session_factory(engine)), create_session_factory(engine)
    finally:
        engine.dispose()


def _permissions(session_factory):
    with session_factory() as session:
        return list(session.scalars(select(PermissionSet).order_by(PermissionSet.id)))


def test_reconcile_creates_catalog_and_permission_set(repository) -> None:
    repo, session_factory = repository
    repo.reconcile_agents_permissions(_config([_permission()]))

    permissions = _permissions(session_factory)
    assert len(permissions) == 1
    assert permissions[0].is_active is True
    with session_factory() as session:
        assert session.scalar(select(PermissionCatalog).where(PermissionCatalog.context == "web"))
        assert session.scalar(select(Agent).where(Agent.key == "podcast"))


def test_reconcile_updates_in_place_and_is_idempotent(repository) -> None:
    repo, session_factory = repository
    initial = _config([_permission(scope=[{"source": "a", "destination": "b"}])])
    repo.reconcile_agents_permissions(initial)
    permission_id = _permissions(session_factory)[0].id

    updated = _config([_permission(scope=[{"destination": "b", "source": "a"}], expiry=3600)])
    repo.reconcile_agents_permissions(updated)
    repo.reconcile_agents_permissions(updated)

    permissions = _permissions(session_factory)
    assert [(permission.id, permission.default_expiry, permission.scope) for permission in permissions] == [
        (permission_id, 3600, '[{"destination":"b","source":"a"}]')
    ]


def test_reconcile_keeps_distinct_scopes_for_the_same_catalog(repository) -> None:
    repo, session_factory = repository
    repo.reconcile_agents_permissions(
        _config([_permission(scope=["one"]), _permission(scope=["two"])])
    )

    assert [permission.scope for permission in _permissions(session_factory)] == [
        '["one"]',
        '["two"]',
    ]


def test_reconcile_deactivates_removed_and_reactivates_restored_permission(repository) -> None:
    repo, session_factory = repository
    configured = _config([_permission()])
    repo.reconcile_agents_permissions(configured)
    repo.reconcile_agents_permissions(_config([]))
    assert _permissions(session_factory)[0].is_active is False

    repo.reconcile_agents_permissions(configured)
    permissions = _permissions(session_factory)
    assert len(permissions) == 1
    assert permissions[0].is_active is True


def test_reconcile_rolls_back_every_change_after_a_failure(repository, monkeypatch) -> None:
    repo, session_factory = repository
    original = repo._reconcile_agent

    def fail_after_first_agent(session, agent):
        original(session, agent)
        raise RuntimeError("database step failed")

    monkeypatch.setattr(repo, "_reconcile_agent", fail_after_first_agent)

    with pytest.raises(RuntimeError, match="database step failed"):
        repo.reconcile_agents_permissions(_config([_permission()]))

    with session_factory() as session:
        assert session.scalars(select(PermissionCatalog)).all() == []
        agents = list(session.scalars(select(Agent)))
        assert [(agent.key, agent.name) for agent in agents] == [
            ("default", "Default Agent")
        ]
        assert session.scalars(select(PermissionSet)).all() == []


def test_reconcile_persists_and_updates_agent_name(repository) -> None:
    repo, session_factory = repository
    config_v1 = AgentsConfig.model_validate(
        {"agents": [{"name": "Hedwig", "key": "podcast", "persona": "P", "instructions": "I", "permissions": []}]}
    )
    repo.reconcile_agents_permissions(config_v1)

    with session_factory() as session:
        agent = session.scalar(select(Agent).where(Agent.key == "podcast"))
        assert agent.name == "Hedwig"

    config_v2 = AgentsConfig.model_validate(
        {"agents": [{"name": "Hedwig Updated", "key": "podcast", "persona": "P", "instructions": "I", "permissions": []}]}
    )
    repo.reconcile_agents_permissions(config_v2)

    with session_factory() as session:
        agent = session.scalar(select(Agent).where(Agent.key == "podcast"))
        assert agent.name == "Hedwig Updated"
