import asyncio

from server.mcp.server import create_mcp_server


def test_mcp_server_exposes_music_play_tracks():
    mcp = create_mcp_server()

    tools = asyncio.run(mcp.list_tools())

    assert [tool.name for tool in tools] == [
        "music.play_tracks",
    ]