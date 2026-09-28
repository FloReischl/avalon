"""Thin MCP tool registration for web capabilities."""

import json
import logging

from mcp.server import MCPServer

from app.services.web_search import WebSearchService
from app.services.web_content import WebContentService


logger = logging.getLogger(__name__)


def register_web_tools(
    mcp: MCPServer, search_service: WebSearchService, content_service: WebContentService
) -> None:
    """Register web tools that delegate to application services."""

    @mcp.tool(name="web.search")
    async def search(query: str) -> list[dict[str, str]]:
        """Search DuckDuckGo for the supplied query."""
        logger.info(
            "tool=web.search request=%s",
            json.dumps({"query": query}, ensure_ascii=False, separators=(",", ":")),
        )
        return await search_service.search(query)

    @mcp.tool(name="web.get-content")
    async def get_content(url: str) -> dict[str, str | bool]:
        """Fetch a URL and return its LLM-ready textual content."""
        logger.info(
            "tool=web.get-content request=%s",
            json.dumps({"url": url}, ensure_ascii=False, separators=(",", ":")),
        )
        return await content_service.get_content(url)
