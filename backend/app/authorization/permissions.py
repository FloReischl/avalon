"""Concrete permission implementations and their registry."""

import json
from datetime import datetime
from pathlib import Path
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

    def allows(self, principal_permission: PrincipalPermission, items: list[object]) -> bool:
        """Return whether the static principal scope permits these items."""
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

    def allows(self, principal_permission: PrincipalPermission, items: list[object]) -> bool:
        del items
        scope = json.loads(principal_permission.scope)
        return isinstance(scope, list) and self._DOMAIN in scope

    def check(
        self,
        principal_permission: PrincipalPermission,
        grant: PermissionGrant,
        items: list[object],
        now: datetime,
    ) -> bool:
        if not self.allows(principal_permission, items):
            return False
        if grant.valid_from > now or grant.valid_to <= now:
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


class WebGetContentPermission:
    """Authorize individual web-content retrieval requests by URL."""

    def allows(self, principal_permission: PrincipalPermission, items: list[object]) -> bool:
        del principal_permission, items
        return True

    def check(
        self,
        principal_permission: PrincipalPermission,
        grant: PermissionGrant,
        items: list[object],
        now: datetime,
    ) -> bool:
        if grant.valid_from > now or grant.valid_to <= now:
            return False
        if principal_permission.validity_type == "range":
            if grant.range is None:
                return False
            return all(item in json.loads(grant.range) for item in items)
        return True

    def format(self, item: object) -> str:
        if not isinstance(item, dict) or not isinstance(item.get("url"), str):
            raise ValueError("web.get-content items require a string URL.")
        return f"Webinhalt abrufen: {item['url']}"

    def items(self, arguments: dict[str, object]) -> list[object]:
        url = arguments.get("url")
        if not isinstance(url, str):
            raise ValueError("web.get-content requires a string URL.")
        return [{"url": url}]

    def approved_arguments(
        self, approved_items: list[object], original_arguments: dict[str, object]
    ) -> dict[str, object] | None:
        del original_arguments
        if not approved_items:
            return None
        item = approved_items[0]
        assert isinstance(item, dict)
        return {"url": item["url"]}


class WorkflowExecutePermission:
    """Authorize workflow execution by the configured workflow-key allowlist."""

    def allows(self, principal_permission: PrincipalPermission, items: list[object]) -> bool:
        scope = json.loads(principal_permission.scope)
        return (
            isinstance(scope, list)
            and len(items) == 1
            and isinstance(items[0], str)
            and items[0] in scope
        )

    def check(
        self,
        principal_permission: PrincipalPermission,
        grant: PermissionGrant,
        items: list[object],
        now: datetime,
    ) -> bool:
        if not self.allows(principal_permission, items):
            return False
        if grant.valid_from > now or grant.valid_to <= now:
            return False
        if principal_permission.validity_type == "range":
            if grant.range is None:
                return False
            return all(item in json.loads(grant.range) for item in items)
        return True

    def format(self, item: object) -> str:
        if not isinstance(item, str):
            raise ValueError("workflow.execute items require a string workflow key.")
        return f"Workflow ausführen: {item}"

    def items(self, arguments: dict[str, object]) -> list[object]:
        workflow_key = arguments.get("workflow_key")
        if not isinstance(workflow_key, str) or not workflow_key.strip():
            raise ValueError("workflow.execute requires a non-empty workflow_key.")
        if "payload" not in arguments:
            raise ValueError("workflow.execute requires payload.")
        return [workflow_key]

    def approved_arguments(
        self, approved_items: list[object], original_arguments: dict[str, object]
    ) -> dict[str, object] | None:
        if not approved_items:
            return None
        workflow_key = approved_items[0]
        assert isinstance(workflow_key, str)
        return {"workflow_key": workflow_key, "payload": original_arguments["payload"]}


class ContentCreateAudioPermission:
    """Authorize audio file creation within principal-allowed path scopes."""

    def allows(self, principal_permission: PrincipalPermission, items: list[object]) -> bool:
        scope = json.loads(principal_permission.scope)
        if not isinstance(scope, list):
            return False
        allowed_dirs = [Path(d).expanduser().resolve() for d in scope if isinstance(d, str)]
        for item in items:
            if not isinstance(item, str):
                return False
            try:
                path = Path(item).expanduser().resolve()
            except Exception:
                return False
            if not any(path.is_relative_to(allowed_dir) for allowed_dir in allowed_dirs):
                return False
        return True

    def check(
        self,
        principal_permission: PrincipalPermission,
        grant: PermissionGrant,
        items: list[object],
        now: datetime,
    ) -> bool:
        if not self.allows(principal_permission, items):
            return False
        if grant.valid_from > now or grant.valid_to <= now:
            return False
        if principal_permission.validity_type == "range":
            if grant.range is None:
                return False
            return all(item in json.loads(grant.range) for item in items)
        return True

    def format(self, item: object) -> str:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("content.create-audio items require a string output file path.")
        return f"Audiodatei erzeugen: {item}"

    def items(self, arguments: dict[str, object]) -> list[object]:
        content = arguments.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("content.create-audio requires a non-empty content string.")
        output_file = arguments.get("output_file")
        if not isinstance(output_file, str) or not output_file.strip() or not output_file.lower().endswith(".mp3"):
            raise ValueError("content.create-audio requires a valid output_file ending with '.mp3'.")
        return [output_file]

    def approved_arguments(
        self, approved_items: list[object], original_arguments: dict[str, object]
    ) -> dict[str, object] | None:
        if not approved_items:
            return None
        output_file = approved_items[0]
        assert isinstance(output_file, str)
        return {"content": original_arguments["content"], "output_file": output_file}


def build_permission_registry() -> PermissionRegistry:
    """Build the registry available in the first authorization slice."""
    registry = PermissionRegistry()
    registry.register("web", "search", WebSearchPermission())
    registry.register("web", "get-content", WebGetContentPermission())
    registry.register("workflow", "execute", WorkflowExecutePermission())
    registry.register("content", "create-audio", ContentCreateAudioPermission())
    return registry
