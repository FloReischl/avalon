import sqlite3

from app.persistence.music_repository import MusicRepository


def test_resolve_track_paths_preserves_input_order_and_skips_unknown_ids(tmp_path):
    db_path = tmp_path / "music.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "CREATE TABLE tracks (id INTEGER PRIMARY KEY, file_path TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO tracks (id, file_path) VALUES (?, ?)",
            [(1, "/music/one.mp3"), (2, "/music/two.mp3"), (3, "/music/three.mp3")],
        )

    result = MusicRepository(str(db_path)).resolve_track_paths([3, 999, 1, 2, 3])

    assert result == [
        "/music/three.mp3",
        "/music/one.mp3",
        "/music/two.mp3",
        "/music/three.mp3",
    ]


def test_resolve_track_paths_accepts_empty_input(tmp_path):
    assert MusicRepository(str(tmp_path / "music.sqlite3")).resolve_track_paths([]) == []
