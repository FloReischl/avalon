from pathlib import Path

import pytest
from sqlalchemy import select

from app.persistence.authorization_repository import AuthorizationRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.persistence.migrations import run_migrations
from app.persistence.models import PermissionCatalog, Principal, PrincipalPermission
from app.user_config import ChatUserConfig


def _config(permissions: list[dict]) -> ChatUserConfig:
    return ChatUserConfig.model_validate(
        {"principal_key": "chat-default", "permissions": permissions}
    )


def _permission(key: str = "search", scope=None, expiry: int = 7200) -> dict:
    return {
        "permission_catalog": {"context": "web", "key": key},
        "principal_permission": {
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


def test_reconcile_creates_chat_principal_and_permissions(repository) -> None:
    repo, session_factory = repository

    repo.reconcile_chat_permissions(
        _config([_permission("search", ["duckduckgo.com"]), _permission("get-content")])
    )

    with session_factory() as session:
        principal = session.scalar(select(Principal).where(Principal.key == "chat-default"))
        assert principal is not None and principal.chat_assignable is True
        permissions = list(session.scalars(select(PrincipalPermission)))
        assert [(permission.scope, permission.is_active) for permission in permissions] == [
            ('["duckduckgo.com"]', True),
            ("[]", True),
        ]
        assert {
            (catalog.context, catalog.key)
            for catalog in session.scalars(select(PermissionCatalog))
        } == {("web", "search"), ("web", "get-content")}


def test_reconcile_updates_and_deactivates_removed_chat_permissions(repository) -> None:
    repo, session_factory = repository
    initial = _config([_permission("search", expiry=7200), _permission("get-content")])
    repo.reconcile_chat_permissions(initial)
    repo.reconcile_chat_permissions(_config([_permission("search", expiry=3600)]))
    repo.reconcile_chat_permissions(_config([_permission("search", expiry=3600)]))

    with session_factory() as session:
        permissions = list(session.scalars(select(PrincipalPermission).order_by(PrincipalPermission.id)))
        assert [(permission.default_expiry, permission.is_active) for permission in permissions] == [
            (3600, True),
            (7200, False),
        ]
        principal = session.scalar(select(Principal).where(Principal.key == "chat-default"))
        assert principal is not None
        principal_id = principal.id

    assert repo.get_principal_permission_catalog_ids(principal_id) == {
        next(
            permission.permission_catalog_id
            for permission in permissions
            if permission.is_active
        )
    }


def test_reconcile_rejects_an_existing_non_chat_principal(repository) -> None:
    repo, session_factory = repository
    with session_factory.begin() as session:
        principal = session.scalar(select(Principal).where(Principal.key == "chat-default"))
        assert principal is not None
        principal.chat_assignable = False

    with pytest.raises(ValueError, match="not chat assignable"):
        repo.reconcile_chat_permissions(_config([]))
