"""Persistence operations for Avalon authorization."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.persistence.models import (
    Agent,
    PermissionCatalog,
    PermissionGrant,
    Principal,
    PrincipalPermission,
)
from app.agents_config import AgentConfig, AgentPermissionConfig, AgentsConfig
from app.user_config import ChatUserConfig


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
                    PrincipalPermission.is_active.is_(True),
                    PermissionCatalog.context == context,
                    PermissionCatalog.key == key,
                )
            )
            return session.scalar(statement)

    def get_permission_catalog_id(self, context: str, key: str) -> int | None:
        """Resolve one MCP permission name to its persistent catalog identity."""
        with self._session_factory() as session:
            return session.scalar(
                select(PermissionCatalog.id).where(
                    PermissionCatalog.context == context,
                    PermissionCatalog.key == key,
                )
            )

    def get_principal_permission_by_catalog_id(
        self, principal_id: int, permission_catalog_id: int
    ) -> PrincipalPermission | None:
        with self._session_factory() as session:
            return session.scalar(
                select(PrincipalPermission).where(
                    PrincipalPermission.principal_id == principal_id,
                    PrincipalPermission.permission_catalog_id == permission_catalog_id,
                    PrincipalPermission.is_active.is_(True),
                )
            )

    def get_principal_permission_catalog_ids(self, principal_id: int) -> set[int]:
        """Return statically cacheable permission IDs, independent of grants."""
        with self._session_factory() as session:
            return set(
                session.scalars(
                    select(PrincipalPermission.permission_catalog_id).where(
                        PrincipalPermission.principal_id == principal_id,
                        PrincipalPermission.is_active.is_(True),
                    )
                )
            )

    def get_principal_capability_names(self, principal_id: int) -> set[str]:
        """Return grantable MCP tool names; grants deliberately do not apply here."""
        with self._session_factory() as session:
            rows = session.execute(
                select(PermissionCatalog.context, PermissionCatalog.key)
                .join(PrincipalPermission)
                .where(
                    PrincipalPermission.principal_id == principal_id,
                    PrincipalPermission.is_active.is_(True),
                )
            )
            return {f"{context}.{key}" for context, key in rows}

    def reconcile_agents_permissions(self, config: AgentsConfig) -> None:
        """Synchronize all configured agent permissions in one DB transaction."""
        with self._session_factory.begin() as session:
            for agent_config in config.agents:
                self._reconcile_agent(session, agent_config)

    def _reconcile_agent(self, session: Session, agent_config: AgentConfig) -> None:
        agent = session.scalar(select(Agent).where(Agent.key == agent_config.key))
        if agent is None:
            principal = Principal(key=f"agent:{agent_config.key}")
            session.add(principal)
            session.flush()
            agent = Agent(key=agent_config.key, principal_id=principal.id)
            session.add(agent)
            session.flush()

        self._reconcile_principal_permissions(
            session, agent.principal_id, agent_config.permissions
        )

    def reconcile_chat_permissions(self, config: ChatUserConfig) -> Principal:
        """Synchronize the configured default chat principal and permissions."""
        with self._session_factory.begin() as session:
            principal = session.scalar(
                select(Principal).where(Principal.key == config.principal_key)
            )
            if principal is None:
                principal = Principal(key=config.principal_key, chat_assignable=True)
                session.add(principal)
                session.flush()
            elif not principal.chat_assignable:
                raise ValueError(
                    f"Configured principal '{config.principal_key}' is not chat assignable."
                )

            self._reconcile_principal_permissions(session, principal.id, config.permissions)
            return principal

    def _reconcile_principal_permissions(
        self,
        session: Session,
        principal_id: int,
        configured_permissions: list[AgentPermissionConfig],
    ) -> None:
        configured_ids: set[tuple[int, str]] = set()
        for configured in configured_permissions:
            catalog_config = configured.permission_catalog
            catalog = session.scalar(
                select(PermissionCatalog).where(
                    PermissionCatalog.context == catalog_config.context,
                    PermissionCatalog.key == catalog_config.key,
                )
            )
            if catalog is None:
                catalog = PermissionCatalog(
                    context=catalog_config.context, key=catalog_config.key
                )
                session.add(catalog)
                session.flush()

            permission_config = configured.principal_permission
            scope = permission_config.canonical_scope
            identity = (catalog.id, scope)
            configured_ids.add(identity)
            permission = session.scalar(
                select(PrincipalPermission).where(
                    PrincipalPermission.principal_id == principal_id,
                    PrincipalPermission.permission_catalog_id == catalog.id,
                    PrincipalPermission.scope == scope,
                )
            )
            if permission is None:
                session.add(
                    PrincipalPermission(
                        principal_id=principal_id,
                        permission_catalog_id=catalog.id,
                        scope=scope,
                        is_active=True,
                        validity_type=permission_config.validity_type,
                        default_expiry=permission_config.default_expiry,
                    )
                )
            else:
                permission.is_active = True
                permission.validity_type = permission_config.validity_type
                permission.default_expiry = permission_config.default_expiry

        permissions = session.scalars(
            select(PrincipalPermission).where(
                PrincipalPermission.principal_id == principal_id
            )
        )
        for permission in permissions:
            if (permission.permission_catalog_id, permission.scope) not in configured_ids:
                permission.is_active = False

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
