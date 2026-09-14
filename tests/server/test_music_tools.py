import asyncio
import json
import logging

from mcp.server import MCPServer

from server.mcp.music import tools


def test_music_play_tracks_executes_resolved_playlist_and_logs_request(
    caplog,
    monkeypatch,
):
    mcp = MCPServer("Test")

    monkeypatch.setattr(
        tools,
        "resolve_track_paths",
        lambda db_path, track_ids: [
            "/music/two.mp3",
            "/music/one.mp3",
        ],
    )

    written = []

    def fake_write_playlist(file_paths):
        written.append(file_paths)
        return "/tmp/avalo_music.m3u"

    started = []

    monkeypatch.setattr(tools, "write_playlist", fake_write_playlist)
    monkeypatch.setattr(
        tools,
        "start_player",
        lambda playlist_path: started.append(playlist_path),
    )

    tools.register_music_tools(mcp, "/music.sqlite3")

    with caplog.at_level(
        logging.INFO,
        logger="server.mcp.music",
    ):
        asyncio.run(
            mcp.call_tool(
                "music.play_tracks",
                {"track_ids": [2, 999, 1]},
            )
        )

    assert written == [
        [
            "/music/two.mp3",
            "/music/one.mp3",
        ]
    ]
    assert started == ["/tmp/avalo_music.m3u"]

    log_record = next(
        record
        for record in caplog.records
        if "tool=music.play_tracks" in record.getMessage()
    )
    payload = log_record.getMessage().split("request=", 1)[1]

    assert json.loads(payload) == {
        "track_ids": [2, 999, 1],
    }
