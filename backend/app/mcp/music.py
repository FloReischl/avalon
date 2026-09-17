"""Thin MCP tool registration for music playback."""

import json
import logging

from mcp.server import MCPServer

from app.services.music import MusicService


logger = logging.getLogger(__name__)


def register_music_tools(mcp: MCPServer, service: MusicService) -> None:
    """Register music tools that delegate to the music application service."""

    @mcp.tool(name="music.play_tracks")
    async def play_tracks(track_ids: list[int]) -> None:
        """Play the supplied track IDs in their given order."""
        logger.info(
            "tool=music.play_tracks request=%s",
            json.dumps(
                {"track_ids": track_ids},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        )
        service.play_tracks(track_ids)
