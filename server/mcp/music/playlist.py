"""M3U playlist creation."""

from pathlib import Path


PLAYLIST_PATH = Path("/tmp/avalo_music.m3u")


def write_playlist(file_paths: list[str]) -> Path:
    """Write file paths to the Avalo music playlist."""
    content = "".join(f"{file_path}\n" for file_path in file_paths)
    PLAYLIST_PATH.write_text(content, encoding="utf-8")
    return PLAYLIST_PATH
