"""MCP server construction for the integrated Avalon backend."""

from typing import Any

from mcp_types import CallToolResult
from mcp.server import MCPServer

from app.authorization.guard import PermissionGuard
from app.authorization.permissions import build_permission_registry
from app.authorization.runtime import get_authorization_request_manager
from app.config import settings
from app.mcp.music import register_music_tools
from app.mcp.web import register_web_tools
from app.persistence.music_repository import MusicRepository
from app.services.music import MusicService
from app.services.web_search import WebSearchService
from app.persistence.authorization_repository import AuthorizationRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.mcp.security import current_principal_id


class AuthorizedMcpServer(MCPServer):
    """Central principal-based discovery and authorization for MCP tools."""

    async def list_tools(self):
        tools = await super().list_tools()
        principal_id = current_principal_id.get()
        if principal_id is None:
            return tools
        allowed = self._principal_capabilities(principal_id)
        return [tool for tool in tools if tool.name in allowed]

    async def call_tool(self, name: str, arguments: dict[str, Any], context=None):
        """Authorize every HTTP MCP capability call before delegation."""
        principal_id = current_principal_id.get()
        if principal_id is None:
            return await super().call_tool(name, arguments, context)
        try:
            permission_context, permission_key = name.split(".", 1)
        except ValueError as exc:
            raise ValueError(f"MCP tool {name!r} has no permission mapping.") from exc

        engine = create_database_engine()
        try:
            registry = build_permission_registry()
            permission = registry.get(permission_context, permission_key)
            guard = PermissionGuard(
                AuthorizationRepository(create_session_factory(engine)),
                registry,
                get_authorization_request_manager(),
            )
            items = permission.items(arguments)
            capability = super().call_tool

            async def authorized_capability(approved_items: list[object]):
                approved_arguments = permission.approved_arguments(approved_items, arguments)
                if approved_arguments is None:
                    return CallToolResult(content=[])
                return await capability(name, approved_arguments, context)

            return await guard.execute(
                principal_id,
                permission_context,
                permission_key,
                items,
                authorized_capability,
                "MCP",
            )
        finally:
            engine.dispose()

    def _principal_capabilities(self, principal_id: int) -> set[str]:
        if not hasattr(self, "_principal_capability_cache"):
            self._principal_capability_cache: dict[int, set[str]] = {}
        cache = self._principal_capability_cache
        if principal_id not in cache:
            engine = create_database_engine()
            try:
                cache[principal_id] = AuthorizationRepository(
                    create_session_factory(engine)
                ).get_principal_capability_names(principal_id)
            finally:
                engine.dispose()
        return cache[principal_id]


def create_mcp_server(
    service: MusicService | None = None,
    web_search_service: WebSearchService | None = None,
) -> MCPServer:
    """Create the MCP server mounted by the FastAPI backend."""
    mcp = AuthorizedMcpServer("Avalon Backend")
    register_music_tools(
        mcp,
        service or MusicService(MusicRepository(settings.music_db_path)),
    )
    register_web_tools(mcp, web_search_service or WebSearchService())
    return mcp
