import asyncio
import json
import logging
from types import SimpleNamespace

from mcp.server import MCPServer
from mcp.server.mcpserver.context import Context

from app.mcp.workflow import register_workflow_tools
from app.mcp.security import current_agent_id
from app.mcp.server import create_mcp_server
import app.mcp.server as mcp_server_module


class FakeWorkflowService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    async def execute(self, workflow_key: str, payload: object, chat_id: int, invocation_id: str, backend_url: str, agent_id: int | None) -> int:
        self.calls.append((workflow_key, payload, chat_id, invocation_id, backend_url, agent_id))
        return 31


def test_workflow_tool_logs_and_delegates_json_payload(caplog) -> None:
    mcp = MCPServer("Test")
    service = FakeWorkflowService()
    register_workflow_tools(mcp, service)  # type: ignore[arg-type]
    payload = {"values": ["a", 2, False]}

    with caplog.at_level(logging.INFO, logger="app.mcp.workflow"):
        context = Context(request_context=SimpleNamespace(meta={"avalon/execution_context": {"chat_id": 42, "invocation_id": "turn-1"}}))
        asyncio.run(mcp.call_tool("workflow.execute", {"workflow_key": "test-workflow", "payload": payload}, context))

    assert service.calls[0][:3] == ("test-workflow", payload, 42)
    assert service.calls[0][3] == "turn-1"
    record = next(record for record in caplog.records if "tool=workflow.execute" in record.message)
    assert json.loads(record.message.split("request=", 1)[1]) == {
        "workflow_key": "test-workflow",
        "payload": payload,
    }


def test_workflow_discovery_is_filtered_by_permission_set(monkeypatch) -> None:
    class FakeEngine:
        def dispose(self) -> None:
            pass

    class FakeRepository:
        def __init__(self, _) -> None:
            pass

        def get_permission_set_catalog_ids(self, agent_id: int) -> set[int]:
            assert agent_id == 7
            return {13}

        def get_permission_catalog_id(self, context: str, key: str) -> int | None:
            return 13 if (context, key) == ("workflow", "execute") else None

    monkeypatch.setattr(mcp_server_module, "AuthorizationRepository", FakeRepository)
    monkeypatch.setattr(mcp_server_module, "create_database_engine", FakeEngine)
    monkeypatch.setattr(mcp_server_module, "create_session_factory", lambda _: object())
    token = current_agent_id.set(7)
    try:
        tools = asyncio.run(create_mcp_server(workflow_service=FakeWorkflowService()).list_tools())  # type: ignore[arg-type]
    finally:
        current_agent_id.reset(token)

    assert [tool.name for tool in tools] == ["workflow.execute"]
