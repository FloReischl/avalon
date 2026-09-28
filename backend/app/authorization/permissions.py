"""Concrete permission implementations and their registry."""

import json
from datetime import datetime
from typing import Protocol

from app.authorization.types import PERMANENT_VALID_TO_YEAR
from app.persistence.models import PermissionGrant, PrincipalPermission


class Permission(Protocol):
    """Permission-specific scope, grant, and item semantics."""

    def check(
        self,
        principal_permission: PrincipalPermission,
        grant: PermissionGrant,
        items: list[object],
        now: datetime,
    ) -> bool:
        ...

    def format(self, item: object) -> str:
        ...

    def items(self, arguments: dict[str, object]) -> list[object]:
        """Translate one MCP tool call into permission-specific items."""
        ...

    def approved_arguments(
        self, approved_items: list[object], original_arguments: dict[str, object]
    ) -> dict[str, object] | None:
        """Return capability arguments, or ``None`` for an empty approval."""
        ...


class PermissionRegistry:
    """Map catalog identifiers to concrete local implementations."""

    def __init__(self) -> None:
        self._permissions: dict[tuple[str, str], Permission] = {}

    def register(self, context: str, key: str, permission: Permission) -> None:
        self._permissions[(context, key)] = permission

    def get(self, context: str, key: str) -> Permission:
        try:
            return self._permissions[(context, key)]
        except KeyError as exc:
            raise ValueError(f"No implementation for permission {context}/{key}.") from exc


class WebSearchPermission:
    """Authorize DuckDuckGo web searches represented as query items."""

    _DOMAIN = "duckduckgo.com"

    def check(
        self,
        principal_permission: PrincipalPermission,
        grant: PermissionGrant,
        items: list[object],
        now: datetime,
    ) -> bool:
        scope = json.loads(principal_permission.scope)
        if self._DOMAIN not in scope:
            return False
        if grant.valid_from > now or grant.valid_to < now:
            return False
        if principal_permission.validity_type == "range":
            if grant.range is None:
                return False
            return all(item in json.loads(grant.range) for item in items)
        return True

    def format(self, item: object) -> str:
        if not isinstance(item, dict) or not isinstance(item.get("query"), str):
            raise ValueError("web.search items require a string query.")
        return f"Websuche bei DuckDuckGo: {item['query']}"

    def items(self, arguments: dict[str, object]) -> list[object]:
        query = arguments.get("query")
        if not isinstance(query, str):
            raise ValueError("web.search requires a string query.")
        return [{"query": query}]

    def approved_arguments(
        self, approved_items: list[object], original_arguments: dict[str, object]
    ) -> dict[str, object] | None:
        del original_arguments
        if not approved_items:
            return None
        query = approved_items[0]
        assert isinstance(query, dict)
        return {"query": query["query"]}


def build_permission_registry() -> PermissionRegistry:
    """Build the registry available in the first authorization slice."""
    registry = PermissionRegistry()
    registry.register("web", "search", WebSearchPermission())
    return registry
