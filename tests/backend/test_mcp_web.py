import asyncio
import json
import logging

import pytest
from mcp.server import MCPServer

from app.authorization.exceptions import PermissionDenied
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


class FakeWebContentService:
    def __init__(self, error: Exception | None = None) -> None:
        self.urls: list[str] = []
        self.error = error

    async def get_content(self, url: str) -> dict[str, str | bool]:
        self.urls.append(url)
        if self.error:
            raise self.error
        return {"url": url, "content": "# Avalon", "truncated": False}


def test_mcp_server_exposes_music_and_web_tools():
    mcp = create_mcp_server(  # type: ignore[arg-type]
        FakeMusicService(), FakeWebSearchService(), FakeWebContentService()
    )

    assert [tool.name for tool in asyncio.run(mcp.list_tools())] == [
        "music.play_tracks",
        "web.search",
        "web.get-content",
    ]


def test_mcp_discovery_filters_only_principal_permissions(monkeypatch):
    lookups = []

    class FakeRepository:
        def __init__(self, _):
            pass

        def get_principal_permission_catalog_ids(self, principal_id):
            lookups.append(principal_id)
            assert principal_id == 7
            return {11}

        def get_permission_catalog_id(self, context, key):
            return 11 if (context, key) == ("web", "search") else None

    class FakeEngine:
        def dispose(self):
            pass

    monkeypatch.setattr(mcp_server_module, "AuthorizationRepository", FakeRepository)
    monkeypatch.setattr(mcp_server_module, "create_database_engine", FakeEngine)
    monkeypatch.setattr(mcp_server_module, "create_session_factory", lambda _: object())
    token = current_principal_id.set(7)
    try:
        mcp = create_mcp_server(
            FakeMusicService(), FakeWebSearchService(), FakeWebContentService()
        )
        tools = asyncio.run(mcp.list_tools())
        assert [tool.name for tool in asyncio.run(mcp.list_tools())] == ["web.search"]
    finally:
        current_principal_id.reset(token)

    assert [tool.name for tool in tools] == ["web.search"]
    assert lookups == [7]


def test_mcp_discovery_exposes_web_content_with_matching_permission(monkeypatch):
    class FakeRepository:
        def __init__(self, _):
            pass

        def get_principal_permission_catalog_ids(self, principal_id):
            assert principal_id == 7
            return {12}

        def get_permission_catalog_id(self, context, key):
            return 12 if (context, key) == ("web", "get-content") else None

    class FakeEngine:
        def dispose(self):
            pass

    monkeypatch.setattr(mcp_server_module, "AuthorizationRepository", FakeRepository)
    monkeypatch.setattr(mcp_server_module, "create_database_engine", FakeEngine)
    monkeypatch.setattr(mcp_server_module, "create_session_factory", lambda _: object())
    token = current_principal_id.set(7)
    try:
        tools = asyncio.run(
            create_mcp_server(
                FakeMusicService(), FakeWebSearchService(), FakeWebContentService()
            ).list_tools()
        )
    finally:
        current_principal_id.reset(token)

    assert [tool.name for tool in tools] == ["web.get-content"]


def test_mcp_call_uses_central_permission_guard(monkeypatch):
    calls = []

    class FakeEngine:
        def dispose(self):
            pass

    class FakeRepository:
        def __init__(self, _):
            pass

        def get_permission_catalog_id(self, context, key):
            return 11 if (context, key) == ("web", "search") else None

    class FakeGuard:
        def __init__(self, *_):
            pass

        async def execute(
            self, principal_id, context, key, items, capability, source_label, **kwargs
        ):
            calls.append((principal_id, context, key, items, source_label, kwargs))
            return await capability(items)

    monkeypatch.setattr(mcp_server_module, "AuthorizationRepository", FakeRepository)
    monkeypatch.setattr(mcp_server_module, "PermissionGuard", FakeGuard)
    monkeypatch.setattr(mcp_server_module, "create_database_engine", FakeEngine)
    monkeypatch.setattr(mcp_server_module, "create_session_factory", lambda _: object())
    service = FakeWebSearchService()
    token = current_principal_id.set(7)
    try:
        asyncio.run(
            create_mcp_server(FakeMusicService(), service, FakeWebContentService()).call_tool(
                "web.search", {"query": "Avalon"}
            )
        )
    finally:
        current_principal_id.reset(token)

    assert calls == [
        (
            7,
            "web",
            "search",
            [{"query": "Avalon"}],
            "MCP",
            {"permission_catalog_id": 11},
        )
    ]
    assert service.queries == ["Avalon"]


def test_mcp_call_denies_a_tool_without_catalog_entry(monkeypatch):
    class FakeEngine:
        def dispose(self):
            pass

    class FakeRepository:
        def __init__(self, _):
            pass

        def get_permission_catalog_id(self, context, key):
            assert (context, key) == ("music", "play_tracks")
            return None

    monkeypatch.setattr(mcp_server_module, "AuthorizationRepository", FakeRepository)
    monkeypatch.setattr(mcp_server_module, "create_database_engine", FakeEngine)
    monkeypatch.setattr(mcp_server_module, "create_session_factory", lambda _: object())
    token = current_principal_id.set(7)
    try:
        with pytest.raises(PermissionDenied, match="music.play_tracks"):
            asyncio.run(
                create_mcp_server(
                    FakeMusicService(), FakeWebSearchService(), FakeWebContentService()
                ).call_tool(
                    "music.play_tracks", {"track_ids": [1]}
                )
            )
    finally:
        current_principal_id.reset(token)


def test_web_tool_logs_full_query_and_delegates(caplog):
    mcp = MCPServer("Test")
    service = FakeWebSearchService()
    register_web_tools(mcp, service, FakeWebContentService())  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO, logger="app.mcp.web"):
        asyncio.run(mcp.call_tool("web.search", {"query": "Avalon local AI"}))

    assert service.queries == ["Avalon local AI"]
    record = next(record for record in caplog.records if "tool=web.search" in record.message)
    assert json.loads(record.message.split("request=", 1)[1]) == {"query": "Avalon local AI"}


def test_web_tool_logs_query_before_provider_error(caplog):
    mcp = MCPServer("Test")
    service = FakeWebSearchService(ConnectionError("provider unavailable"))
    register_web_tools(mcp, service, FakeWebContentService())  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO, logger="app.mcp.web"):
        with pytest.raises(Exception, match="Error executing tool web.search"):
            asyncio.run(mcp.call_tool("web.search", {"query": "Avalon local AI"}))

    assert service.queries == ["Avalon local AI"]
    assert any("tool=web.search" in record.message for record in caplog.records)


def test_web_get_content_tool_logs_url_and_delegates(caplog):
    mcp = MCPServer("Test")
    service = FakeWebContentService()
    register_web_tools(mcp, FakeWebSearchService(), service)  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO, logger="app.mcp.web"):
        asyncio.run(mcp.call_tool("web.get-content", {"url": "https://example.test"}))

    assert service.urls == ["https://example.test"]
    record = next(
        record for record in caplog.records if "tool=web.get-content" in record.message
    )
    assert json.loads(record.message.split("request=", 1)[1]) == {
        "url": "https://example.test"
    }
