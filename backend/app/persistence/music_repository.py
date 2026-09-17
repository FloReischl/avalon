"""SQLite access for external music playback data."""

import sqlite3


class MusicRepository:
    """Resolve music track identifiers through the configured music database."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def resolve_track_paths(self, track_ids: list[int]) -> list[str]:
        """Resolve existing IDs to paths in input order, omitting unknown IDs."""
        if not track_ids:
            return []

        placeholders = ",".join("?" for _ in track_ids)
        with sqlite3.connect(self._db_path) as connection:
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
