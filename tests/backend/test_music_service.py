from pathlib import Path

import pytest

from app.services.music import MusicService


class FakeMusicRepository:
    def __init__(self, paths: list[str]) -> None:
        self.paths = paths
        self.track_ids: list[int] | None = None

    def resolve_track_paths(self, track_ids: list[int]) -> list[str]:
        self.track_ids = track_ids
        return self.paths


def test_play_tracks_orchestrates_repository_playlist_and_player():
    repository = FakeMusicRepository(["/music/two.mp3", "/music/one.mp3"])
    written = []
    started = []

    service = MusicService(
        repository,  # type: ignore[arg-type]
        playlist_writer=lambda paths: written.append(paths) or Path("/tmp/music.m3u"),
        player_starter=started.append,
    )

    service.play_tracks([2, 999, 1])

    assert repository.track_ids == [2, 999, 1]
    assert written == [["/music/two.mp3", "/music/one.mp3"]]
    assert started == [Path("/tmp/music.m3u")]


def test_play_tracks_preserves_repository_errors():
    class BrokenRepository:
        def resolve_track_paths(self, track_ids: list[int]) -> list[str]:
            raise OSError("database unavailable")

    service = MusicService(BrokenRepository())  # type: ignore[arg-type]

    with pytest.raises(OSError, match="database unavailable"):
        service.play_tracks([1])
