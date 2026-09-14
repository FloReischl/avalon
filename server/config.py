"""Configuration for the standalone Avalo server."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Static settings for the initial local server setup."""

    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8096
    music_db_path: str = "/media/flo/2TB_SSD/music/mp3db.sqlite3"
    log_path: str = "/tmp/avalo_server.log"


settings = Settings()
