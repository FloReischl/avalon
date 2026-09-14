from pathlib import Path

from server.mcp.music import player


def test_start_player_starts_celluloid(monkeypatch):
    calls = []

    def fake_popen(command, **kwargs):
        calls.append((command, kwargs))

    monkeypatch.setattr(player.subprocess, "Popen", fake_popen)

    player.start_player(Path("/tmp/playlist.m3u"))

    assert calls == [
        (
            ["celluloid", "/tmp/playlist.m3u"],
            {"start_new_session": True},
        )
    ]
