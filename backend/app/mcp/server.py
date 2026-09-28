"""MCP server construction for the integrated Avalon backend."""

from mcp.server import MCPServer

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
    """MCP discovery filtered by the principal carried by the HTTP boundary."""

    async def list_tools(self):
        tools = await super().list_tools()
        principal_id = current_principal_id.get()
        if principal_id is None:
            return tools
        engine = create_database_engine()
        try:
            allowed = AuthorizationRepository(create_session_factory(engine)).get_principal_capability_names(principal_id)
        finally:
            engine.dispose()
        return [tool for tool in tools if tool.name in allowed]


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
