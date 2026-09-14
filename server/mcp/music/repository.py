"""SQLite access for music execution data."""

import sqlite3


def resolve_track_paths(
    db_path: str,
    track_ids: list[int],
) -> list[str]:
    """Resolve existing track IDs to file paths in input order."""
    if not track_ids:
        return []

    placeholders = ",".join("?" for _ in track_ids)

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT id, file_path
            FROM tracks
            WHERE id IN ({placeholders})
            """,
            track_ids,
        ).fetchall()

    paths_by_id = {
        track_id: file_path
        for track_id, file_path in rows
    }

    return [
        paths_by_id[track_id]
        for track_id in track_ids
        if track_id in paths_by_id
    ]
