"""Persistence operations for Avalon authorization."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.persistence.models import (
    Agent,
    Chat,
    PermissionCatalog,
    PermissionGrant,
    PermissionSet,
)
from app.agents_config import AgentConfig, AgentPermissionConfig, AgentsConfig
from app.authorization.types import PERMANENT_VALID_TO_YEAR


class AuthorizationRepository:
    """Store agent-owned permission definitions and grants."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_agent_by_key(self, key: str) -> Agent | None:
        with self._session_factory() as session:
            return session.scalar(select(Agent).where(Agent.key == key))

    def get_agent_by_id(self, agent_id: int) -> Agent | None:
        with self._session_factory() as session:
            return session.get(Agent, agent_id)

    def get_permission_set(self, agent_id: int, context: str, key: str) -> PermissionSet | None:
        with self._session_factory() as session:
            statement = (
                select(PermissionSet)
                .join(PermissionCatalog)
                .where(
                    PermissionSet.agent_id == agent_id,
                    PermissionSet.is_active.is_(True),
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

    def get_permission_set_by_catalog_id(
        self, agent_id: int, permission_catalog_id: int
    ) -> PermissionSet | None:
        with self._session_factory() as session:
            return session.scalar(
                select(PermissionSet).where(
                    PermissionSet.agent_id == agent_id,
                    PermissionSet.permission_catalog_id == permission_catalog_id,
                    PermissionSet.is_active.is_(True),
                )
            )

    def get_permission_set_catalog_ids(self, agent_id: int) -> set[int]:
        """Return statically cacheable permission IDs, independent of grants."""
        with self._session_factory() as session:
            return set(
                session.scalars(
                    select(PermissionSet.permission_catalog_id).where(
                        PermissionSet.agent_id == agent_id,
                        PermissionSet.is_active.is_(True),
                    )
                )
            )

    def get_agent_capability_names(self, agent_id: int) -> set[str]:
        """Return grantable MCP tool names; grants deliberately do not apply here."""
        with self._session_factory() as session:
            rows = session.execute(
                select(PermissionCatalog.context, PermissionCatalog.key)
                .join(PermissionSet)
                .where(
                    PermissionSet.agent_id == agent_id,
                    PermissionSet.is_active.is_(True),
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
            agent = Agent(
                key=agent_config.key,
                name=agent_config.name,
                icon=agent_config.icon,
            )
            session.add(agent)
            session.flush()
        else:
            agent.name = agent_config.name
            agent.icon = agent_config.icon
            session.flush()

        self._reconcile_permission_sets(session, agent.id, agent_config.permissions)

    def _reconcile_permission_sets(
        self,
        session: Session,
        agent_id: int,
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

            permission_config = configured.permission_set
            scope = permission_config.canonical_scope
            identity = (catalog.id, scope)
            configured_ids.add(identity)
            permission = session.scalar(
                select(PermissionSet).where(
                    PermissionSet.agent_id == agent_id,
                    PermissionSet.permission_catalog_id == catalog.id,
                    PermissionSet.scope == scope,
                )
            )
            if permission is None:
                session.add(
                    PermissionSet(
                        agent_id=agent_id,
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
            select(PermissionSet).where(
                PermissionSet.agent_id == agent_id
            )
        )
        for permission in permissions:
            if (permission.permission_catalog_id, permission.scope) not in configured_ids:
                permission.is_active = False

    def get_grants(self, permission_set_id: int) -> list[PermissionGrant]:
        with self._session_factory() as session:
            return list(
                session.scalars(
                    select(PermissionGrant).where(
                        PermissionGrant.permission_set_id == permission_set_id
                    )
                )
            )

    def get_agent_id_for_chat(self, chat_id: int) -> int | None:
        """Resolve the authorization agent stored by a chat."""
        with self._session_factory() as session:
            chat = session.get(Chat, chat_id)
            return None if chat is None else chat.agent_id

    def get_active_grant(
        self, permission_set_id: int, now: datetime
    ) -> PermissionGrant | None:
        """Return the longest currently effective grant for display/editing."""
        with self._session_factory() as session:
            return session.scalar(
                select(PermissionGrant)
                .where(
                    PermissionGrant.permission_set_id == permission_set_id,
                    PermissionGrant.valid_from <= now,
                    PermissionGrant.valid_to > now,
                )
                .order_by(PermissionGrant.valid_to.desc(), PermissionGrant.id.desc())
            )

    def get_active_permission_sets(
        self, agent_id: int
    ) -> list[tuple[PermissionSet, PermissionCatalog]]:
        """Return all active permission definitions for one agent."""
        with self._session_factory() as session:
            return list(
                session.execute(
                    select(PermissionSet, PermissionCatalog)
                    .join(PermissionCatalog)
                    .where(
                        PermissionSet.agent_id == agent_id,
                        PermissionSet.is_active.is_(True),
                    )
                    .order_by(PermissionCatalog.context, PermissionCatalog.key)
                )
            )

    def save_proactive_grant(
        self,
        permission_set_id: int,
        validity_type: str,
        expires_at: datetime | None,
        now: datetime,
    ) -> PermissionGrant:
        """Create or update the one displayed direct grant without a request."""
        with self._session_factory.begin() as session:
            permission = session.get(PermissionSet, permission_set_id)
            if permission is None or not permission.is_active:
                raise KeyError("Permission set does not exist.")
            if permission.validity_type != validity_type:
                raise ValueError("Permission validity type does not match.")
            if validity_type == "range":
                raise ValueError("Range grants require capability request items.")
            if validity_type == "duration" and expires_at is None:
                raise ValueError("Duration grants require expires_at.")
            if validity_type == "permanent" and expires_at is not None:
                raise ValueError("Permanent grants do not accept expires_at.")

            grant = session.scalar(
                select(PermissionGrant)
                .where(
                    PermissionGrant.permission_set_id == permission_set_id,
                    PermissionGrant.valid_from <= now,
                    PermissionGrant.valid_to > now,
                )
                .order_by(PermissionGrant.valid_to.desc(), PermissionGrant.id.desc())
            )
            valid_to = (
                expires_at
                if validity_type == "duration"
                else datetime(PERMANENT_VALID_TO_YEAR, 1, 1)
            )
            if grant is None:
                grant = PermissionGrant(
                    permission_set_id=permission_set_id,
                    valid_from=now,
                    valid_to=valid_to,
                    range=None,
                )
                session.add(grant)
            else:
                grant.valid_to = valid_to
            session.flush()
            session.refresh(grant)
            return grant

    def revoke_proactive_grant(
        self,
        permission_set_id: int,
        now: datetime,
    ) -> None:
        """Remove any currently active grant for this proactive permission."""
        with self._session_factory.begin() as session:
            grants = session.scalars(
                select(PermissionGrant)
                .where(
                    PermissionGrant.permission_set_id == permission_set_id,
                    PermissionGrant.valid_from <= now,
                    PermissionGrant.valid_to > now,
                )
            ).all()
            for grant in grants:
                session.delete(grant)

    def create_grant(
        self,
        permission_set_id: int,
        valid_from: datetime,
        valid_to: datetime,
        item_range: str | None,
    ) -> PermissionGrant:
        with self._session_factory() as session:
            grant = PermissionGrant(
                permission_set_id=permission_set_id,
                valid_from=valid_from,
                valid_to=valid_to,
                range=item_range,
            )
            session.add(grant)
            session.commit()
            session.refresh(grant)
            return grant
