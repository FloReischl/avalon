import sqlite3

from server.mcp.music.repository import resolve_track_paths


def test_resolve_track_paths_preserves_input_order_and_skips_unknown_ids(tmp_path):
    db_path = tmp_path / "music.sqlite3"

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE tracks (
                id INTEGER PRIMARY KEY,
                file_path TEXT NOT NULL UNIQUE
            )
            """
        )
        connection.executemany(
            "INSERT INTO tracks (id, file_path) VALUES (?, ?)",
            [
                (1, "/music/one.mp3"),
                (2, "/music/two.mp3"),
                (3, "/music/three.mp3"),
            ],
        )

    result = resolve_track_paths(
        str(db_path),
        [3, 999, 1, 2],
    )

    assert result == [
        "/music/three.mp3",
        "/music/one.mp3",
        "/music/two.mp3",
    ]


def test_resolve_track_paths_accepts_empty_input(tmp_path):
    db_path = tmp_path / "music.sqlite3"

    assert resolve_track_paths(str(db_path), []) == []
