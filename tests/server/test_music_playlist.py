from server.mcp.music import playlist


def test_write_playlist_preserves_track_order(tmp_path, monkeypatch):
    playlist_path = tmp_path / "playlist.m3u"
    monkeypatch.setattr(playlist, "PLAYLIST_PATH", playlist_path)

    result = playlist.write_playlist(
        [
            "/music/three.mp3",
            "/music/one.mp3",
            "/music/two.mp3",
        ]
    )

    assert result == playlist_path
    assert playlist_path.read_text(encoding="utf-8") == (
        "/music/three.mp3\n"
        "/music/one.mp3\n"
        "/music/two.mp3\n"
    )
