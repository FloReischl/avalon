import asyncio
import json
import sqlite3
from pathlib import Path

import pytest
from mcp import Client

from server.config import settings
from server.mcp.music.playlist import PLAYLIST_PATH


MCP_URL = f"http://{settings.mcp_host}:{settings.mcp_port}/mcp"


@pytest.skip(reason="required: a running MCP server and DB with music tracks available")
@pytest.mark.integration
def test_music_play_tracks_over_real_mcp_server():
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

    log_text = Path(settings.log_path).read_text(encoding="utf-8")
    expected_payload = json.dumps(
        {"track_ids": track_ids},
        ensure_ascii=False,
        separators=(",", ":"),
    )

    assert f"tool=music.play_tracks request={expected_payload}" in log_text