"""Application service for music playback."""

from collections.abc import Callable
from pathlib import Path

from app.music.player import start_player
from app.music.playlist import write_playlist
from app.persistence.music_repository import MusicRepository


class MusicService:
    """Turn requested track IDs into a Celluloid playlist playback."""

    def __init__(
        self,
        repository: MusicRepository,
        *,
        playlist_writer: Callable[[list[str]], Path] = write_playlist,
        player_starter: Callable[[Path], None] = start_player,
    ) -> None:
        self._repository = repository
        self._playlist_writer = playlist_writer
        self._player_starter = player_starter

    def play_tracks(self, track_ids: list[int]) -> None:
        """Resolve tracks, write a playlist, then start Celluloid."""
        file_paths = self._repository.resolve_track_paths(track_ids)
        playlist_path = self._playlist_writer(file_paths)
        self._player_starter(playlist_path)
