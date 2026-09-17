"""MCP server construction for the integrated Avalo backend."""

from mcp.server import MCPServer

from app.config import settings
from app.mcp.music import register_music_tools
from app.persistence.music_repository import MusicRepository
from app.services.music import MusicService


def create_mcp_server(service: MusicService | None = None) -> MCPServer:
    """Create the MCP server mounted by the FastAPI backend."""
    mcp = MCPServer("Avalo Backend")
    register_music_tools(
        mcp,
        service or MusicService(MusicRepository(settings.music_db_path)),
    )
    return mcp
