"""MCP server construction."""

from mcp.server import MCPServer

from server.config import settings
from server.mcp.music.tools import register_music_tools


def create_mcp_server() -> MCPServer:
    """Create and configure the Avalo MCP server."""
    mcp = MCPServer("Avalo Server")
    register_music_tools(mcp, settings.music_db_path)
    return mcp
