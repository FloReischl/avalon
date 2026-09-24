"""MCP server construction for the integrated Avalon backend."""

from mcp.server import MCPServer

from app.config import settings
from app.mcp.music import register_music_tools
from app.mcp.web import register_web_tools
from app.persistence.music_repository import MusicRepository
from app.services.music import MusicService
from app.services.web_search import WebSearchService


def create_mcp_server(
    service: MusicService | None = None,
    web_search_service: WebSearchService | None = None,
) -> MCPServer:
    """Create the MCP server mounted by the FastAPI backend."""
    mcp = MCPServer("Avalon Backend")
    register_music_tools(
        mcp,
        service or MusicService(MusicRepository(settings.music_db_path)),
    )
    register_web_tools(mcp, web_search_service or WebSearchService())
    return mcp
