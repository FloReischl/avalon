import asyncio
import json
import logging
from types import SimpleNamespace

from httpx import ASGITransport, AsyncClient
from mcp.server import MCPServer

import app.main as main_module
from app.mcp.security import bearer_token_for_agent
from app.mcp.music import register_music_tools
from app.mcp.server import create_mcp_server


class FakeMusicService:
    def __init__(self) -> None:
        self.track_ids: list[int] | None = None

    def play_tracks(self, track_ids: list[int]) -> None:
        self.track_ids = track_ids


def test_mcp_server_exposes_music_and_web_tools():
    mcp = create_mcp_server(FakeMusicService())  # type: ignore[arg-type]

    tools = asyncio.run(mcp.list_tools())

    assert [tool.name for tool in tools] == [
        "music.play_tracks",
        "web.search",
        "web.get-content",
        "workflow.execute",
        "content.create-audio",
        "file.copy",
    ]


def test_music_tool_logs_request_and_delegates_to_service(caplog):
    mcp = MCPServer("Test")
    service = FakeMusicService()
    register_music_tools(mcp, service)  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO, logger="app.mcp.music"):
        asyncio.run(mcp.call_tool("music.play_tracks", {"track_ids": [2, 999, 1]}))

    assert service.track_ids == [2, 999, 1]
    log_record = next(
        record for record in caplog.records
        if "tool=music.play_tracks" in record.getMessage()
    )
    assert json.loads(log_record.getMessage().split("request=", 1)[1]) == {
        "track_ids": [2, 999, 1],
    }


def test_mcp_is_available_at_backend_mcp_path(monkeypatch):
    monkeypatch.setattr(
        main_module,
        "initialize_user_config",
        lambda: SimpleNamespace(chat=object()),
    )
    monkeypatch.setattr(main_module, "load_agents_config", lambda: SimpleNamespace(agents=[]))
    monkeypatch.setattr(main_module, "initialize_workflows_config", lambda: object())
    monkeypatch.setattr(main_module, "initialize_avalon_state", lambda *_: None)
    monkeypatch.setattr(main_module, "run_migrations", lambda: None)
    monkeypatch.setattr(
        main_module,
        "AuthorizationRepository",
        lambda _: SimpleNamespace(
            reconcile_chat_permissions=lambda _: None,
            reconcile_agents_permissions=lambda _: None,
        ),
    )

    async def validate_llms(*_: object) -> None:
        pass

    monkeypatch.setattr(main_module, "validate_configured_llms", validate_llms)

    async def request_mcp():
        application = main_module.create_app()
        async with application.router.lifespan_context(application):
            transport = ASGITransport(app=application)
            async with AsyncClient(
                transport=transport,
                base_url="http://127.0.0.1:8095",
                follow_redirects=True,
            ) as client:
                return await client.post(
                    "/mcp",
                    headers={
                        "Accept": "application/json, text/event-stream",
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {bearer_token_for_agent(1)}",
                    },
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-11-25",
                            "capabilities": {},
                            "clientInfo": {"name": "test", "version": "1"},
                        },
                    },
                )

    response = asyncio.run(request_mcp())

    assert response.status_code == 200
    assert '"name":"Avalon Backend"' in response.text


def test_mcp_rejects_missing_bearer_token(monkeypatch):
    monkeypatch.setattr(main_module, "initialize_user_config", lambda: object())

    async def request_mcp():
        application = main_module.create_app()
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://127.0.0.1:8095") as client:
            return await client.post("/mcp", json={})

    response = asyncio.run(request_mcp())

    assert response.status_code == 401
    assert response.json() == {"detail": "Bearer token required."}
