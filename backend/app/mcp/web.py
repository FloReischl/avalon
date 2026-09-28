"""Thin MCP tool registration for web search."""

import json
import logging

from mcp.server import MCPServer

from app.authorization.guard import PermissionGuard
from app.authorization.permissions import build_permission_registry
from app.authorization.runtime import get_authorization_request_manager
from app.mcp.security import current_principal_id
from app.persistence.authorization_repository import AuthorizationRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.services.web_search import WebSearchService


logger = logging.getLogger(__name__)


def register_web_tools(mcp: MCPServer, service: WebSearchService) -> None:
    """Register web tools that delegate to the web search application service."""

    @mcp.tool(name="web.search")
    async def search(query: str) -> list[dict[str, str]]:
        """Search DuckDuckGo for the supplied query."""
        logger.info(
            "tool=web.search request=%s",
            json.dumps({"query": query}, ensure_ascii=False, separators=(",", ":")),
        )
        principal_id = current_principal_id.get()
        if principal_id is None:
            # Registration-level tests use MCP in-process. HTTP calls always set it.
            return await service.search(query)
        engine = create_database_engine()
        try:
            guard = PermissionGuard(
                AuthorizationRepository(create_session_factory(engine)),
                build_permission_registry(),
                get_authorization_request_manager(),
            )

            async def capability(approved: list[object]) -> list[dict[str, str]]:
                if not approved:
                    return []
                item = approved[0]
                assert isinstance(item, dict)
                return await service.search(item["query"])

            return await guard.execute(
                principal_id, "web", "search", [{"query": query}], capability, "MCP"
            )
        finally:
            engine.dispose()
