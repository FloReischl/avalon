"""Focused contracts for the shared SSE notification hub."""

import asyncio

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.router import api_router
from app.api.routes import events as events_route
from app.authorization.requests import AuthorizationRequestManager
from app.services.notification_hub import NotificationHub
from app.services.workflow_events import WorkflowEventManager, WorkflowExecutionEvent
from app.workflow_confirmations import WorkflowConfirmationManager


async def _next_after_ready(stream, publish) -> str:
    next_event = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)
    publish()
    return await next_event


def test_notification_hub_initializes_and_routes_all_producers() -> None:
    async def scenario() -> None:
        authorization = AuthorizationRequestManager()
        confirmations = WorkflowConfirmationManager()
        workflows = WorkflowEventManager()
        stream = NotificationHub(authorization, confirmations, workflows).events()
        try:
            assert await anext(stream) == 'event: authorization_requests_changed\ndata: {}\n\n'
            assert await anext(stream) == 'event: workflow_confirmations_changed\ndata: {}\n\n'
            assert await anext(stream) == 'event: workflow_execution\ndata: {}\n\n'

            authorization_event = await _next_after_ready(
                stream,
                lambda: authorization.create("web", "search", [], [], "permanent", 0),
            )
            confirmation_event = await _next_after_ready(
                stream,
                lambda: confirmations.create(
                    42,
                    {"title": "Review", "columns": []},
                    [],
                ),
            )
            workflow_event = await _next_after_ready(
                stream,
                lambda: workflows.publish(WorkflowExecutionEvent(42, "running", ["Started"])),
            )

            assert authorization_event == 'event: authorization_requests_changed\ndata: {}\n\n'
            assert confirmation_event == 'event: workflow_confirmations_changed\ndata: {}\n\n'
            assert workflow_event == (
                'event: workflow_execution\ndata: '
                '{"workflow_execution_id": 42, "state": "running", "progress_content": ["Started"]}\n\n'
            )
        finally:
            await stream.aclose()

    asyncio.run(scenario())


def test_notification_hub_keeps_subscribers_isolated_and_cleans_up_on_cancellation() -> None:
    async def scenario() -> None:
        authorization = AuthorizationRequestManager()
        confirmations = WorkflowConfirmationManager()
        workflows = WorkflowEventManager()
        first = NotificationHub(authorization, confirmations, workflows).events()
        second = NotificationHub(authorization, confirmations, workflows).events()
        try:
            for stream in (first, second):
                await anext(stream)
                await anext(stream)
                await anext(stream)

            next_first = asyncio.create_task(anext(first))
            next_second = asyncio.create_task(anext(second))
            await asyncio.sleep(0)
            workflows.publish(WorkflowExecutionEvent(7, "completed", None))
            assert '"workflow_execution_id": 7' in await next_first
            assert '"workflow_execution_id": 7' in await next_second

            waiting = asyncio.create_task(anext(first))
            await asyncio.sleep(0)
            waiting.cancel()
            try:
                await waiting
            except asyncio.CancelledError:
                pass
            # The cancelled first client is gone; the still-open second client remains.
            assert len(authorization._listeners) == 1
            assert len(confirmations._listeners) == 1
            assert len(workflows._subscribers) == 1
        finally:
            await first.aclose()
            await second.aclose()
        assert not authorization._listeners
        assert not confirmations._listeners
        assert not workflows._subscribers

    asyncio.run(scenario())


def test_notification_hub_emits_a_keepalive_when_idle() -> None:
    async def scenario() -> None:
        stream = NotificationHub(
            AuthorizationRequestManager(),
            WorkflowConfirmationManager(),
            WorkflowEventManager(),
            keepalive_seconds=0.001,
        ).events()
        try:
            await anext(stream)
            await anext(stream)
            await anext(stream)
            assert await anext(stream) == ": keepalive\n\n"
        finally:
            await stream.aclose()

    asyncio.run(scenario())


def test_notification_hub_forwards_nearly_simultaneous_events() -> None:
    async def scenario() -> None:
        authorization = AuthorizationRequestManager()
        workflows = WorkflowEventManager()
        stream = NotificationHub(
            authorization, WorkflowConfirmationManager(), workflows
        ).events()
        try:
            await anext(stream)
            await anext(stream)
            await anext(stream)
            next_event = asyncio.create_task(anext(stream))
            await asyncio.sleep(0)
            authorization.create("web", "search", [], [], "permanent", 0)
            workflows.publish(WorkflowExecutionEvent(8, "running", None))
            first = await next_event
            second = await anext(stream)
            assert {first, second} == {
                'event: authorization_requests_changed\ndata: {}\n\n',
                'event: workflow_execution\ndata: '
                '{"workflow_execution_id": 8, "state": "running", "progress_content": null}\n\n',
            }
        finally:
            await stream.aclose()

    asyncio.run(scenario())


def test_notification_hub_cleans_up_a_partial_subscription_failure() -> None:
    class FailingConfirmationManager:
        def subscribe(self):
            raise RuntimeError("broken subscription")

        def unsubscribe(self, queue) -> None:
            raise AssertionError("No confirmation queue was created.")

    async def scenario() -> None:
        authorization = AuthorizationRequestManager()
        stream = NotificationHub(
            authorization,
            FailingConfirmationManager(),
            WorkflowEventManager(),
        ).events()
        try:
            try:
                await anext(stream)
            except RuntimeError as exc:
                assert str(exc) == "broken subscription"
            else:
                raise AssertionError("The failed subscription must reach the caller.")
            assert not authorization._listeners
        finally:
            await stream.aclose()

    asyncio.run(scenario())


def test_shared_events_route_has_the_sse_contract(monkeypatch) -> None:
    class FiniteHub:
        def __init__(self, *args) -> None:
            pass

        async def events(self):
            yield ": test\n\n"

    async def request():
        application = FastAPI()
        application.include_router(events_route.router, prefix="/api/v1")
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            return await client.get("/api/v1/events")

    monkeypatch.setattr(events_route, "NotificationHub", FiniteHub)
    response = asyncio.run(request())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")


def test_api_router_exposes_only_the_shared_notification_stream() -> None:
    legacy_paths = {
        "/api/v1/authorization-requests/events",
        "/api/v1/workflow-executions/confirmations/events",
        "/api/v1/workflow-executions/events",
    }
    paths = {
        f"{included.include_context.prefix}{route.path}"
        for included in api_router.routes
        for route in included.original_router.routes
        if hasattr(route, "path")
    }

    assert "/api/v1/events" in paths
    assert paths.isdisjoint(legacy_paths)
