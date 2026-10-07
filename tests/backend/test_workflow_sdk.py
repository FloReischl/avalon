"""Focused contracts for the workflow micro-SDK confirmation call."""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "workflows"))

import avalon_workflows.client as client_module
from avalon_workflows import AvalonWorkflowClient, ConfirmationCancelled


SCHEMA = {"title": "Review", "columns": [{"key": "title", "type": "str"}]}
ROWS = [{"title": "Original"}]
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

    assert asyncio.run(workflow_client().confirm(SCHEMA, ROWS)) == RESULT
    assert calls == [
        {"client": {"headers": {"Authorization": "Bearer parent-agent-token"}, "timeout": 3600}},
        {
            "url": "http://127.0.0.1:8095/api/v1/workflow-executions/42/confirmation",
            "json": {"schema": SCHEMA, "rows": ROWS},
        },
    ]


def test_confirm_maps_only_the_explicit_cancel_response(monkeypatch) -> None:
    install_fake_http(monkeypatch, FakeResponse(409, {"detail": "workflow_confirmation_cancelled"}))

    with pytest.raises(ConfirmationCancelled):
        asyncio.run(workflow_client().confirm(SCHEMA, ROWS))


def test_confirm_keeps_validation_and_other_runtime_errors(monkeypatch) -> None:
    response = FakeResponse(400, {"detail": "invalid confirmation input"})
    install_fake_http(monkeypatch, response)

    with pytest.raises(RuntimeError, match="HTTP 400"):
        asyncio.run(workflow_client().confirm(SCHEMA, ROWS))
    assert response.raise_called


def test_confirm_does_not_treat_other_conflicts_as_cancel(monkeypatch) -> None:
    response = FakeResponse(409, {"detail": "Workflow execution is not running."})
    install_fake_http(monkeypatch, response)

    with pytest.raises(RuntimeError, match="HTTP 409"):
        asyncio.run(workflow_client().confirm(SCHEMA, ROWS))
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
        asyncio.run(workflow_client().confirm(SCHEMA, ROWS))
    assert attempts == 1
