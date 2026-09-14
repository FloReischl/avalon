"""Music player process integration."""

from pathlib import Path
import subprocess


def start_player(playlist_path: Path) -> None:
    """Start Celluloid with the generated playlist."""
    subprocess.Popen(
        ["celluloid", str(playlist_path)],
        start_new_session=True,
    )
