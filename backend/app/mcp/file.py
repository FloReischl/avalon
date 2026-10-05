"""Thin MCP registration for filesystem copy operations."""

from mcp.server import MCPServer

from app.authorization.exceptions import PermissionDenied
from app.services.file_copy import FileCopyService


def register_file_tools(mcp: MCPServer, service: FileCopyService) -> None:
    """Register the ``file.copy`` capability."""

    @mcp.tool(name="file.copy")
    async def copy(source: str, destination: str) -> None:
        del source, destination, service
        raise PermissionDenied("file.copy requires the authorized MCP execution path.")
