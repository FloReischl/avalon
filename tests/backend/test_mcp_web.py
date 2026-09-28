import asyncio
import json
import logging

import pytest
from mcp.server import MCPServer

from app.mcp.server import create_mcp_server
from app.mcp.web import register_web_tools
from app.mcp.security import current_principal_id
import app.mcp.server as mcp_server_module


class FakeMusicService:
    def play_tracks(self, track_ids: list[int]) -> None:
        pass


class FakeWebSearchService:
    def __init__(self, error: Exception | None = None) -> None:
        self.queries: list[str] = []
        self.error = error

    async def search(self, query: str) -> list[dict[str, str]]:
        self.queries.append(query)
        if self.error:
            raise self.error
        return [{"title": "Avalon", "url": "https://example.test", "snippet": "Local AI"}]


def test_mcp_server_exposes_music_and_web_tools():
    mcp = create_mcp_server(FakeMusicService(), FakeWebSearchService())  # type: ignore[arg-type]

    assert [tool.name for tool in asyncio.run(mcp.list_tools())] == [
        "music.play_tracks",
        "web.search",
    ]


def test_mcp_discovery_filters_only_principal_permissions(monkeypatch):
    class FakeRepository:
        def __init__(self, _):
            pass

        def get_principal_capability_names(self, principal_id):
            assert principal_id == 7
            return {"web.search"}

    class FakeEngine:
        def dispose(self):
            pass

    monkeypatch.setattr(mcp_server_module, "AuthorizationRepository", FakeRepository)
    monkeypatch.setattr(mcp_server_module, "create_database_engine", FakeEngine)
    monkeypatch.setattr(mcp_server_module, "create_session_factory", lambda _: object())
    token = current_principal_id.set(7)
    try:
        tools = asyncio.run(
            create_mcp_server(FakeMusicService(), FakeWebSearchService()).list_tools()
        )
    finally:
        current_principal_id.reset(token)

    assert [tool.name for tool in tools] == ["web.search"]


def test_web_tool_logs_full_query_and_delegates(caplog):
    mcp = MCPServer("Test")
    service = FakeWebSearchService()
    register_web_tools(mcp, service)  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO, logger="app.mcp.web"):
        asyncio.run(mcp.call_tool("web.search", {"query": "Avalon local AI"}))

    assert service.queries == ["Avalon local AI"]
    record = next(record for record in caplog.records if "tool=web.search" in record.message)
    assert json.loads(record.message.split("request=", 1)[1]) == {"query": "Avalon local AI"}


def test_web_tool_logs_query_before_provider_error(caplog):
    mcp = MCPServer("Test")
    service = FakeWebSearchService(ConnectionError("provider unavailable"))
    register_web_tools(mcp, service)  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO, logger="app.mcp.web"):
        with pytest.raises(Exception, match="Error executing tool web.search"):
            asyncio.run(mcp.call_tool("web.search", {"query": "Avalon local AI"}))

    assert service.queries == ["Avalon local AI"]
    assert any("tool=web.search" in record.message for record in caplog.records)
