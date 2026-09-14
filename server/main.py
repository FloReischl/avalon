"""Entry point for the standalone Avalo server."""

from server.config import settings
from server.logging import configure_logging
from server.mcp.server import create_mcp_server


def main() -> None:
    """Start the Avalo MCP server."""
    configure_logging(settings.log_path)

    mcp = create_mcp_server()
    mcp.run(
        transport="streamable-http",
        host=settings.mcp_host,
        port=settings.mcp_port,
    )


if __name__ == "__main__":
    main()
