"""Thin MCP tool registration for content audio creation."""

from __future__ import annotations

import logging

from mcp.server import MCPServer
from app.services.audio_creation import AudioCreationService


logger = logging.getLogger(__name__)


def register_content_tools(mcp: MCPServer, service: AudioCreationService) -> None:
    """Register content tools that delegate to AudioCreationService."""

    @mcp.tool(name="content.create-audio")
    async def create_audio(content: str, output_file: str) -> None:
        """Create MP3 audio from text content."""
        logger.info("tool=content.create-audio request=%s", {"output_file": output_file})
        await service.create_audio(content=content, output_file=output_file)
