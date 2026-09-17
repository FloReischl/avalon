import asyncio
import sqlite3
import socket
from pathlib import Path

import pytest
from mcp import Client

from app.config import settings
from app.music.playlist import PLAYLIST_PATH


MCP_URL = f"http://{settings.api_host}:{settings.api_port}/mcp"


def _music_mcp_infrastructure_available() -> bool:
    if not Path(settings.music_db_path).is_file():
        return False

    with socket.socket() as connection:
        return connection.connect_ex((settings.api_host, settings.api_port)) == 0


@pytest.mark.skipif(
    not _music_mcp_infrastructure_available(),
    reason="requires a running Avalo backend and music database",
)
@pytest.mark.integration
def test_music_play_tracks_over_real_mcp_backend():
    with sqlite3.connect(settings.music_db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, file_path
            FROM tracks
            ORDER BY id
            LIMIT 2
            """
        ).fetchall()

    assert len(rows) == 2

    track_ids = [row[0] for row in rows]
    expected_paths = [row[1] for row in rows]

    async def call_tool():
        async with Client(MCP_URL) as client:
            return await client.call_tool(
                "music.play_tracks",
                {"track_ids": track_ids},
            )

    result = asyncio.run(call_tool())

    assert result.is_error is False
    assert PLAYLIST_PATH.read_text(encoding="utf-8").splitlines() == expected_paths
