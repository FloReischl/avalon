"""Focused contracts for the workflow micro-SDK confirmation call."""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from mcp import types as mcp_types

sys.path.insert(0, str(Path(__file__).parents[2] / "workflows"))

import avalon_workflows.client as client_module
from avalon_workflows import (
    AvalonWorkflowClient,
    ConfirmationCancelled,
    ConfirmationTable,
)



CONFIRMATION = {
    "schema": {"title": "Review", "columns": [{"key": "title", "type": "str"}]},
    "rows": [{"title": "Original"}],
}
RESULT = [{"title": "Edited", "avalon_confirmation": "approved"}]



def workflow_client() -> AvalonWorkflowClient:
    return AvalonWorkflowClient(
        {
            "avalon": {
                "backend_url": "http://127.0.0.1:8095/",
                "workflow_execution_id": 42,
                "bearer_token": "parent-agent-token",
            }
        }
    )


class FakeResponse:
    def __init__(self, status_code: int, body: object) -> None:
        self.status_code = status_code
        self._body = body
        self.raise_called = False

    def json(self) -> object:
        return self._body

    def raise_for_status(self) -> None:
        self.raise_called = True
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def install_fake_http(monkeypatch, response: FakeResponse) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []

    class FakeHttpClient:
        def __init__(self, **kwargs) -> None:
            calls.append({"client": kwargs})

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, url: str, *, json: object) -> FakeResponse:
            calls.append({"url": url, "json": json})
            return response

    monkeypatch.setattr(client_module.httpx2, "AsyncClient", FakeHttpClient)
    return calls


def test_confirm_posts_unmodified_input_with_runtime_auth_and_returns_rows(monkeypatch) -> None:
    calls = install_fake_http(monkeypatch, FakeResponse(200, RESULT))

    assert asyncio.run(workflow_client().confirm(CONFIRMATION)
) == RESULT
    assert calls == [
        {"client": {"headers": {"Authorization": "Bearer parent-agent-token"}, "timeout": 3600}},
        {
            "url": "http://127.0.0.1:8095/api/v1/workflow-executions/42/confirmation",
            "json": CONFIRMATION,

        },
    ]


def test_confirm_accepts_confirmation_table(monkeypatch) -> None:
    calls = install_fake_http(monkeypatch, FakeResponse(200, RESULT))
    table = (
        ConfirmationTable("Review")
        .column("title", str, editable=True)
        .column("publish", bool)
    )
    table.rows.add(["Original", True])

    assert asyncio.run(workflow_client().confirm(table)) == RESULT
    assert calls[1]["json"] == table.to_dict()


def test_confirm_maps_only_the_explicit_cancel_response(monkeypatch) -> None:

    install_fake_http(monkeypatch, FakeResponse(409, {"detail": "workflow_confirmation_cancelled"}))

    with pytest.raises(ConfirmationCancelled):
        asyncio.run(workflow_client().confirm(CONFIRMATION)
)


def test_confirm_keeps_validation_and_other_runtime_errors(monkeypatch) -> None:
    response = FakeResponse(400, {"detail": "invalid confirmation input"})
    install_fake_http(monkeypatch, response)

    with pytest.raises(RuntimeError, match="HTTP 400"):
        asyncio.run(workflow_client().confirm(CONFIRMATION)
)
    assert response.raise_called


def test_confirm_does_not_treat_other_conflicts_as_cancel(monkeypatch) -> None:
    response = FakeResponse(409, {"detail": "Workflow execution is not running."})
    install_fake_http(monkeypatch, response)

    with pytest.raises(RuntimeError, match="HTTP 409"):
        asyncio.run(workflow_client().confirm(CONFIRMATION)
)
    assert response.raise_called


def test_confirm_propagates_transport_errors_without_retry(monkeypatch) -> None:
    attempts = 0

    class FakeHttpClient:
        def __init__(self, **_kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, *_args, **_kwargs) -> None:
            nonlocal attempts
            attempts += 1
            raise OSError("connection lost")

    monkeypatch.setattr(client_module.httpx2, "AsyncClient", FakeHttpClient)

    with pytest.raises(OSError, match="connection lost"):
        asyncio.run(workflow_client().confirm(CONFIRMATION)
)
    assert attempts == 1


def test_mail_methods_delegate_to_the_matching_mcp_capability(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    results: dict[str, object] = {
        "mail.get_provider_stats": {"all_messages_count": 3},
        "mail.get_messages": {"result": [{"message_id": "message-1"}]},
        "mail.get_messages_by_thread": {"result": [{"message_id": "message-1"}]},
        "mail.get_mail": {"message_id": "message-1"},
        "mail.get_attachment": {"content_base64": "Ynl0ZXM="},
        "mail.get_categories": {"result": ["Project"]},
    }

    async def fake_call_tool(name: str, arguments: dict[str, object]) -> object:
        calls.append((name, arguments))
        return results.get(name)

    client = workflow_client()
    monkeypatch.setattr(client, "call_tool", fake_call_tool)
    timestamp = datetime(2026, 10, 1, tzinfo=timezone.utc)

    assert asyncio.run(client.set_mail_provider("gmail")) is None
    assert asyncio.run(client.get_mail_provider_stats()) == {"all_messages_count": 3}
    assert asyncio.run(
        client.get_mail_messages("INBOX", since=timestamp, before=None)
    ) == [{"message_id": "message-1"}]
    assert asyncio.run(client.get_mail_messages_by_thread("thread-1")) == [
        {"message_id": "message-1"}
    ]
    assert asyncio.run(client.get_mail("message-1", as_text=False)) == {
        "message_id": "message-1"
    }
    assert asyncio.run(client.get_mail_attachment("message-1", "attachment-1")) == {
        "content_base64": "Ynl0ZXM="
    }
    assert asyncio.run(client.get_mail_categories()) == ["Project"]
    assert asyncio.run(client.create_mail_categories(["Project"])) is None
    assert asyncio.run(
        client.set_mail_categories("message-1", ["Project"], archive=True, mark_unread=True)
    ) is None
    assert asyncio.run(client.unset_mail_categories("message-1", ["Project"])) is None

    assert calls == [
        ("mail.set_provider", {"provider": "gmail"}),
        ("mail.get_provider_stats", {}),
        ("mail.get_messages", {"category": "INBOX", "since": timestamp, "before": None}),
        ("mail.get_messages_by_thread", {"thread_id": "thread-1"}),
        ("mail.get_mail", {"message_id": "message-1", "as_text": False}),
        ("mail.get_attachment", {"message_id": "message-1", "attachment_id": "attachment-1"}),
        ("mail.get_categories", {}),
        ("mail.create_categories", {"categories": ["Project"]}),
        (
            "mail.set_categories",
            {
                "message_id": "message-1",
                "categories": ["Project"],
                "archive": True,
                "mark_unread": True,
            },
        ),
        ("mail.unset_categories", {"message_id": "message-1", "categories": ["Project"]}),
    ]


def test_mail_methods_preserve_mcp_errors(monkeypatch) -> None:
    async def failing_call_tool(_name: str, _arguments: dict[str, object]) -> object:
        raise RuntimeError("MCP denied the call")

    client = workflow_client()
    monkeypatch.setattr(client, "call_tool", failing_call_tool)

    with pytest.raises(RuntimeError, match="MCP denied the call"):
        asyncio.run(client.get_mail_categories())


def test_mail_method_optional_parameters_use_the_mcp_defaults(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    async def fake_call_tool(name: str, arguments: dict[str, object]) -> object:
        calls.append((name, arguments))
        return {"result": []} if name == "mail.get_messages" else {}

    client = workflow_client()
    monkeypatch.setattr(client, "call_tool", fake_call_tool)

    assert asyncio.run(client.get_mail_messages("INBOX")) == []
    assert asyncio.run(client.get_mail("message-1")) == {}
    assert asyncio.run(client.set_mail_categories("message-1", ["Project"])) is None

    assert calls == [
        ("mail.get_messages", {"category": "INBOX", "since": None, "before": None}),
        ("mail.get_mail", {"message_id": "message-1", "as_text": True}),
        (
            "mail.set_categories",
            {
                "message_id": "message-1",
                "categories": ["Project"],
                "archive": False,
                "mark_unread": None,
            },
        ),
    ]


def test_mcp_serializes_mail_message_datetime_arguments_as_json() -> None:
    since = datetime(2026, 10, 1, 12, 30, tzinfo=timezone.utc)
    request = mcp_types.CallToolRequest(
        params=mcp_types.CallToolRequestParams(
            name="mail.get_messages",
            arguments={"category": "INBOX", "since": since, "before": None},
        )
    )

    assert request.model_dump(
        by_alias=True,
        mode="json",
        exclude_unset=True,
    ) == {
        "params": {
            "name": "mail.get_messages",
            "arguments": {
                "category": "INBOX",
                "since": "2026-10-01T12:30:00Z",
                "before": None,
            },
        }
    }
