"""Thin MCP tool registration for web search."""

import json
import logging

from mcp.server import MCPServer

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
        return await service.search(query)
