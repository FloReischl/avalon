"""Persistence operations for Avalon authorization."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.persistence.models import (
    PermissionCatalog,
    PermissionGrant,
    Principal,
    PrincipalPermission,
)


class AuthorizationRepository:
    """Store principals, permission definitions, and grants."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_principal_by_key(self, key: str) -> Principal | None:
        with self._session_factory() as session:
            return session.scalar(select(Principal).where(Principal.key == key))

    def get_principal_permission(
        self, principal_id: int, context: str, key: str
    ) -> PrincipalPermission | None:
        with self._session_factory() as session:
            statement = (
                select(PrincipalPermission)
                .join(PermissionCatalog)
                .where(
                    PrincipalPermission.principal_id == principal_id,
                    PermissionCatalog.context == context,
                    PermissionCatalog.key == key,
                )
            )
            return session.scalar(statement)

    def get_grants(self, principal_permission_id: int) -> list[PermissionGrant]:
        with self._session_factory() as session:
            return list(
                session.scalars(
                    select(PermissionGrant).where(
                        PermissionGrant.principal_permission_id
                        == principal_permission_id
                    )
                )
            )

    def create_grant(
        self,
        principal_permission_id: int,
        valid_from: datetime,
        valid_to: datetime,
        item_range: str | None,
    ) -> PermissionGrant:
        with self._session_factory() as session:
            grant = PermissionGrant(
                principal_permission_id=principal_permission_id,
                valid_from=valid_from,
                valid_to=valid_to,
                range=item_range,
            )
            session.add(grant)
            session.commit()
            session.refresh(grant)
            return grant

    def bootstrap_chat_default_web_search(
        self, principal_key: str
    ) -> Principal:
        """Idempotently provision the configured default chat principal."""
        with self._session_factory() as session:
            principal = session.scalar(
                select(Principal).where(Principal.key == principal_key)
            )
            if principal is None:
                principal = Principal(key=principal_key, chat_assignable=True)
                session.add(principal)
                session.flush()
            elif not principal.chat_assignable:
                raise ValueError(
                    f"Configured principal '{principal_key}' is not chat assignable."
                )

            catalog = session.scalar(
                select(PermissionCatalog).where(
                    PermissionCatalog.context == "web",
                    PermissionCatalog.key == "search",
                )
            )
            if catalog is None:
                catalog = PermissionCatalog(context="web", key="search")
                session.add(catalog)
                session.flush()

            definition = session.scalar(
                select(PrincipalPermission).where(
                    PrincipalPermission.principal_id == principal.id,
                    PrincipalPermission.permission_catalog_id == catalog.id,
                )
            )
            if definition is None:
                session.add(
                    PrincipalPermission(
                        principal_id=principal.id,
                        permission_catalog_id=catalog.id,
                        scope='["duckduckgo.com"]',
                        validity_type="duration",
                        default_expiry=36_000,
                    )
                )
            session.commit()
            session.refresh(principal)
            return principal
