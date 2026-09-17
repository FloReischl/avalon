from pathlib import Path

from app.music import player, playlist


def test_write_playlist_preserves_track_order(tmp_path, monkeypatch):
    playlist_path = tmp_path / "playlist.m3u"
    monkeypatch.setattr(playlist, "PLAYLIST_PATH", playlist_path)

    result = playlist.write_playlist(["/music/three.mp3", "/music/one.mp3"])

    assert result == playlist_path
    assert playlist_path.read_text(encoding="utf-8") == "/music/three.mp3\n/music/one.mp3\n"


def test_start_player_starts_celluloid(monkeypatch):
    calls = []

    def fake_popen(command, **kwargs):
        calls.append((command, kwargs))

    monkeypatch.setattr(player.subprocess, "Popen", fake_popen)

    player.start_player(Path("/tmp/playlist.m3u"))

    assert calls == [(["celluloid", "/tmp/playlist.m3u"], {"start_new_session": True})]
