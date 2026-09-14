"""MCP tools for music playback."""

import json
import logging

from mcp.server import MCPServer

from server.mcp.music.player import start_player
from server.mcp.music.playlist import write_playlist
from server.mcp.music.repository import resolve_track_paths


logger = logging.getLogger("server.mcp.music")


def register_music_tools(
    mcp: MCPServer,
    db_path: str,
) -> None:
    """Register music tools on the Avalo MCP server."""

    @mcp.tool(name="music.play_tracks")
    def play_tracks(track_ids: list[int]) -> None:
        """Play the supplied track IDs in their given order."""
        logger.info(
            "tool=music.play_tracks request=%s",
            json.dumps(
                {"track_ids": track_ids},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        )

        file_paths = resolve_track_paths(db_path, track_ids)
        playlist_path = write_playlist(file_paths)
        start_player(playlist_path)
