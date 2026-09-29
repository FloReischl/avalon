"""Focused tests for the first authorization vertical slice."""

import asyncio
import json
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.api.routes.chat import stream_chat_response
from app.authorization.exceptions import AbortException, AuthorizationTimeout, PermissionDenied
from app.authorization.guard import PermissionGuard
from app.authorization.permissions import build_permission_registry
from app.authorization.requests import AuthorizationRequestManager
from app.authorization.types import AuthorizationRequest
from app.services.chat import ChatTurn
from app.services.tool_runner import ToolRunner


class FakeAuthorizationRepository:
    def __init__(self, definition=None, grants=None):
        self.definition = definition
        self.grants = grants or []
        self.created = []

    def get_principal_permission(self, principal_id, context, key):
        del principal_id, context, key
        return self.definition

    def get_grants(self, principal_permission_id):
        del principal_permission_id
        return self.grants

    def create_grant(self, *args):
        self.created.append(args)


def definition():
    return SimpleNamespace(
        id=7,
        scope='["duckduckgo.com"]',
        validity_type="duration",
        default_expiry=36_000,
    )


def workflow_definition(scope: object):
    return SimpleNamespace(
        id=8,
        scope=json.dumps(scope),
        validity_type="permanent",
        default_expiry=0,
    )


def active_grant():
    return SimpleNamespace(
        valid_from=datetime.now() - timedelta(seconds=1),
        valid_to=datetime.now() + timedelta(seconds=1),
        range=None,
    )


@pytest.mark.asyncio
async def test_workflow_scope_allows_only_its_registered_key():
    guard = PermissionGuard(
        FakeAuthorizationRepository(workflow_definition(["test-workflow"]), [active_grant()]),
        build_permission_registry(),
        AuthorizationRequestManager(),
    )
    executed = []

    async def capability(items):
        executed.extend(items)

    await guard.execute(1, "workflow", "execute", ["test-workflow"], capability)

    assert executed == ["test-workflow"]


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", [[], ["other-workflow"]])
async def test_workflow_scope_denies_unlisted_or_empty_keys(scope):
    guard = PermissionGuard(
        FakeAuthorizationRepository(workflow_definition(scope), [active_grant()]),
        build_permission_registry(),
        AuthorizationRequestManager(),
    )
    executed = False

    async def capability(items):
        nonlocal executed
        del items
        executed = True

    with pytest.raises(PermissionDenied, match="principal scope"):
        await guard.execute(1, "workflow", "execute", ["test-workflow"], capability)

    assert not executed


@pytest.mark.asyncio
async def test_workflow_scope_denies_empty_items() -> None:
    guard = PermissionGuard(
        FakeAuthorizationRepository(workflow_definition(["test-workflow"]), [active_grant()]),
        build_permission_registry(),
        AuthorizationRequestManager(),
    )
    executed = False

    async def capability(items):
        nonlocal executed
        del items
        executed = True

    with pytest.raises(PermissionDenied, match="principal scope"):
        await guard.execute(1, "workflow", "execute", [], capability)

    assert not executed


def test_web_content_has_no_static_scope_restriction():
    permission = build_permission_registry().get("web", "get-content")

    assert permission.allows(SimpleNamespace(scope="[]"), [{"url": "https://example.test"}])


@pytest.mark.asyncio
async def test_guard_waits_for_confirmation_and_uses_only_selected_items():
    repository = FakeAuthorizationRepository(definition())
    manager = AuthorizationRequestManager()
    captured = []
    guard = PermissionGuard(
        repository, build_permission_registry(), manager, captured.append
    )
    executed = []

    async def capability(items):
        executed.extend(items)
        return "ok"

    task = asyncio.create_task(
        guard.execute(1, "web", "search", [{"query": "Avalon"}], capability)
    )
    await asyncio.sleep(0)
    assert captured[0].formatted_items == ["Websuche bei DuckDuckGo: Avalon"]
    manager.confirm(captured[0].id, [0], 3600)

    assert await task == "ok"
    assert executed == [{"query": "Avalon"}]
    assert len(repository.created) == 1


@pytest.mark.asyncio
async def test_guard_denies_without_creating_a_request():
    manager = AuthorizationRequestManager()
    guard = PermissionGuard(
        FakeAuthorizationRepository(), build_permission_registry(), manager
    )

    with pytest.raises(PermissionDenied):
        await guard.execute(1, "web", "search", [{"query": "Avalon"}], lambda _: None)


@pytest.mark.asyncio
async def test_abort_exception_stops_waiting_guard():
    manager = AuthorizationRequestManager()
    requests = []
    guard = PermissionGuard(
        FakeAuthorizationRepository(definition()),
        build_permission_registry(),
        manager,
        requests.append,
    )

    async def capability(items):
        del items
        return "not reached"

    task = asyncio.create_task(
        guard.execute(1, "web", "search", [{"query": "Avalon"}], capability)
    )
    await asyncio.sleep(0)
    manager.abort(requests[0].id)
    with pytest.raises(AbortException):
        await task


@pytest.mark.asyncio
async def test_request_manager_times_out_and_removes_request():
    manager = AuthorizationRequestManager(timeout_seconds=0.001)
    request = manager.create("web", "search", [], [], "duration", 1)
    with pytest.raises(AuthorizationTimeout):
        await manager.wait(request.id)
    with pytest.raises(KeyError):
        manager.abort(request.id)


class FakeToolRuntime:
    def __init__(self):
        self.responses = [
            {"tool_calls": [{"function": {"name": "web.search", "arguments": {"query": "Avalon"}}}]},
            {"content": "Hier ist das Ergebnis."},
        ]

    async def generate_tool_response_stream(self, messages, tools):
        assert tools
        yield self.responses.pop(0)


class FakeGuard:
    def __init__(self):
        self.execute_calls = 0

    async def execute(self, principal_id, context, key, items, capability, source_label):
        self.execute_calls += 1
        assert (principal_id, context, key) == (3, "web", "search")
        return await capability(items)


class FakeMcpClient:
    def __init__(self):
        self.calls = 0

    async def list_tools(self):
        return [{"type": "function", "function": {"name": "web.search", "parameters": {}}}]

    async def call_tool(self, name, arguments):
        assert (name, arguments) == ("web.search", {"query": "Avalon"})
        self.calls += 1
        return [{"title": "Avalon", "url": "https://example.test", "snippet": "ok"}]


@pytest.mark.asyncio
async def test_tool_runner_returns_final_text_after_authorized_tool_result():
    ToolRunner._tool_definition_cache = {}
    runner = ToolRunner(FakeToolRuntime(), lambda principal_id: FakeMcpClient())
    assert [chunk async for chunk in runner.stream_response(3, [{"role": "user", "content": "Suche Avalon"}], "Chat: Suche")] == ["Hier ist das Ergebnis."]


@pytest.mark.asyncio
async def test_tool_runner_reuses_a_duplicate_web_search_result_within_one_turn():
    ToolRunner._tool_definition_cache = {}
    duplicate_call = {
        "tool_calls": [
            {"function": {"name": "web.search", "arguments": {"query": "Avalon"}}}
        ]
    }

    class RepeatingToolRuntime:
        def __init__(self):
            self.responses = [duplicate_call, duplicate_call, {"content": "Fertig."}]

        async def generate_tool_response_stream(self, messages, tools):
            assert tools
            yield self.responses.pop(0)

    client = FakeMcpClient()
    runner = ToolRunner(RepeatingToolRuntime(), lambda principal_id: client)

    assert [
        chunk
        async for chunk in runner.stream_response(
            3, [{"role": "user", "content": "Suche Avalon"}], "Chat: Suche"
        )
    ] == ["Fertig."]
    assert client.calls == 1


@pytest.mark.asyncio
async def test_tool_runner_caches_discovery_for_a_principal():
    ToolRunner._tool_definition_cache = {}

    class Runtime:
        async def generate_tool_response_stream(self, messages, tools):
            yield {"content": "Fertig."}

    class Client:
        def __init__(self):
            self.list_calls = 0

        async def list_tools(self):
            self.list_calls += 1
            return []

        async def call_tool(self, name, arguments):
            raise AssertionError("not reached")

    client = Client()
    for _ in range(2):
        runner = ToolRunner(Runtime(), lambda principal_id: client)
        assert [chunk async for chunk in runner.stream_response(3, [], "Chat")] == ["Fertig."]
    assert client.list_calls == 1


@pytest.mark.asyncio
async def test_chat_sse_waits_for_authorization_without_emitting_a_second_ui_event():
    class Service:
        async def stream_response(self, turn):
            del turn
            yield "Antwort"

        async def finalize_turn(self, turn):
            del turn

    stream = stream_chat_response(Service(), ChatTurn(1, []))
    assert "event: chat" in await anext(stream)
    assert "event: chunk" in await anext(stream)
    assert "event: done" in await anext(stream)
