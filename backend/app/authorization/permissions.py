"""Concrete permission implementations and their registry."""

import json
from datetime import datetime
from pathlib import Path
from typing import Protocol

from app.authorization.types import PERMANENT_VALID_TO_YEAR
from app.persistence.models import PermissionGrant, PermissionSet
from app.services.file_copy import FileCopyScope


class Permission(Protocol):
    """Permission-specific scope, grant, and item semantics."""

    def check(
        self,
        permission_set: PermissionSet,
        grant: PermissionGrant,
        items: list[object],
        now: datetime,
    ) -> bool:
        ...

    def allows(self, permission_set: PermissionSet, items: list[object]) -> bool:
        """Return whether the static agent scope permits these items."""
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

    def allows(self, permission_set: PermissionSet, items: list[object]) -> bool:
        del items
        scope = json.loads(permission_set.scope)
        return isinstance(scope, list) and self._DOMAIN in scope

    def check(
        self,
        permission_set: PermissionSet,
        grant: PermissionGrant,
        items: list[object],
        now: datetime,
    ) -> bool:
        if not self.allows(permission_set, items):
            return False
        if grant.valid_from > now or grant.valid_to <= now:
            return False
        if permission_set.validity_type == "range":
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

    def allows(self, permission_set: PermissionSet, items: list[object]) -> bool:
        del permission_set, items
        return True

    def check(
        self,
        permission_set: PermissionSet,
        grant: PermissionGrant,
        items: list[object],
        now: datetime,
    ) -> bool:
        if grant.valid_from > now or grant.valid_to <= now:
            return False
        if permission_set.validity_type == "range":
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

    def allows(self, permission_set: PermissionSet, items: list[object]) -> bool:
        scope = json.loads(permission_set.scope)
        return (
            isinstance(scope, list)
            and len(items) == 1
            and isinstance(items[0], str)
            and items[0] in scope
        )

    def check(
        self,
        permission_set: PermissionSet,
        grant: PermissionGrant,
        items: list[object],
        now: datetime,
    ) -> bool:
        if not self.allows(permission_set, items):
            return False
        if grant.valid_from > now or grant.valid_to <= now:
            return False
        if permission_set.validity_type == "range":
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
    """Authorize audio file creation within agent-allowed path scopes."""

    def allows(self, permission_set: PermissionSet, items: list[object]) -> bool:
        scope = json.loads(permission_set.scope)
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
        permission_set: PermissionSet,
        grant: PermissionGrant,
        items: list[object],
        now: datetime,
    ) -> bool:
        if not self.allows(permission_set, items):
            return False
        if grant.valid_from > now or grant.valid_to <= now:
            return False
        if permission_set.validity_type == "range":
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


class FileCopyPermission:
    """Authorize one copy operation against paired source/destination roots."""

    @staticmethod
    def _path(value: object, field: str) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"file.copy requires a non-empty {field} path.")
        path = Path(value).expanduser()
        if not path.is_absolute() or ".." in path.parts:
            raise ValueError(f"file.copy {field} must be an absolute path without '..'.")
        return path

    def allows(self, permission_set: PermissionSet, items: list[object]) -> bool:
        return self.scope_for(permission_set, items) is not None

    def scope_for(
        self, permission_set: PermissionSet, items: list[object]
    ) -> FileCopyScope | None:
        if len(items) != 1 or not isinstance(items[0], dict):
            return None
        source = self._path(items[0].get("source"), "source")
        destination = self._path(items[0].get("destination"), "destination")
        try:
            scope = json.loads(permission_set.scope)
        except json.JSONDecodeError:
            return None
        if not isinstance(scope, list):
            return None
        for entry in scope:
            if not isinstance(entry, dict):
                continue
            try:
                source_root = self._path(entry.get("source"), "scope source")
                destination_root = self._path(entry.get("destination"), "scope destination")
            except ValueError:
                continue
            if source.is_relative_to(source_root) and destination.is_relative_to(destination_root):
                return FileCopyScope(source_root, destination_root)
        return None

    def check(
        self,
        permission_set: PermissionSet,
        grant: PermissionGrant,
        items: list[object],
        now: datetime,
    ) -> bool:
        if not self.allows(permission_set, items):
            return False
        if grant.valid_from > now or grant.valid_to <= now:
            return False
        if permission_set.validity_type == "range":
            if grant.range is None:
                return False
            return all(item in json.loads(grant.range) for item in items)
        return True

    def format(self, item: object) -> str:
        if not isinstance(item, dict):
            raise ValueError("file.copy items require source and destination paths.")
        return f"Datei kopieren: {item['source']} nach {item['destination']}"

    def items(self, arguments: dict[str, object]) -> list[object]:
        source = arguments.get("source")
        destination = arguments.get("destination")
        self._path(source, "source")
        self._path(destination, "destination")
        return [{"source": source, "destination": destination}]

    def approved_arguments(
        self, approved_items: list[object], original_arguments: dict[str, object]
    ) -> dict[str, object] | None:
        del original_arguments
        if not approved_items:
            return None
        item = approved_items[0]
        assert isinstance(item, dict)
        return {"source": item["source"], "destination": item["destination"]}


class MailReadPermission:
    """Authorize read-only mail access as one capability-level operation."""

    def allows(self, permission_set: PermissionSet, items: list[object]) -> bool:
        del items
        scope = json.loads(permission_set.scope)
        return isinstance(scope, list) and (not scope or "read" in scope)

    def check(self, permission_set: PermissionSet, grant: PermissionGrant, items: list[object], now: datetime) -> bool:
        if not self.allows(permission_set, items):
            return False
        if grant.valid_from > now or grant.valid_to <= now:
            return False
        if permission_set.validity_type == "range":
            return grant.range is not None and all(item in json.loads(grant.range) for item in items)
        return True

    def format(self, item: object) -> str:
        if not isinstance(item, str):
            raise ValueError("mail.read items require an operation name.")
        return f"E-Mails lesen: {item}"

    def items(self, arguments: dict[str, object]) -> list[object]:
        del arguments
        return ["read"]

    def approved_arguments(self, approved_items: list[object], original_arguments: dict[str, object]) -> dict[str, object] | None:
        return original_arguments if approved_items else None


class MailWritePermission(MailReadPermission):
    """Authorize mail mutations as one capability-level operation."""

    def allows(self, permission_set: PermissionSet, items: list[object]) -> bool:
        del items
        scope = json.loads(permission_set.scope)
        return isinstance(scope, list) and "write" in scope

    def format(self, item: object) -> str:
        if not isinstance(item, str):
            raise ValueError("mail.write items require an operation name.")
        return f"E-Mail-Kategorien ändern: {item}"

    def items(self, arguments: dict[str, object]) -> list[object]:
        del arguments
        return ["write"]


def build_permission_registry() -> PermissionRegistry:
    """Build the registry available in the first authorization slice."""
    registry = PermissionRegistry()
    registry.register("web", "search", WebSearchPermission())
    registry.register("web", "get-content", WebGetContentPermission())
    registry.register("workflow", "execute", WorkflowExecutePermission())
    registry.register("content", "create-audio", ContentCreateAudioPermission())
    registry.register("file", "copy", FileCopyPermission())
    registry.register("mail", "read", MailReadPermission())
    registry.register("mail", "write", MailWritePermission())
    return registry
