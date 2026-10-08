"""Aggregate Avalon invalidations into one SSE stream per client."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass

from app.authorization.requests import AuthorizationRequestManager
from app.services.workflow_events import WorkflowEventManager, WorkflowExecutionEvent
from app.workflow_confirmations import WorkflowConfirmationManager


@dataclass(frozen=True, slots=True)
class _Subscription:
    event_type: str
    queue: asyncio.Queue[object]
    unsubscribe: Callable[[asyncio.Queue[object]], None]


class NotificationHub:
    """Subscribe one client to each existing notification producer."""

    def __init__(
        self,
        authorization_requests: AuthorizationRequestManager,
        workflow_confirmations: WorkflowConfirmationManager,
        workflow_events: WorkflowEventManager,
        *,
        keepalive_seconds: float = 15.0,
    ) -> None:
        self._authorization_requests = authorization_requests
        self._workflow_confirmations = workflow_confirmations
        self._workflow_events = workflow_events
        self._keepalive_seconds = keepalive_seconds

    async def events(self) -> AsyncIterator[str]:
        """Yield initial invalidations followed by routed producer events."""
        subscriptions = self._subscribe()
        try:
            for subscription in subscriptions:
                yield _sse(subscription.event_type, {})

            while True:
                tasks = {
                    asyncio.create_task(subscription.queue.get()): subscription
                    for subscription in subscriptions
                }
                try:
                    await asyncio.wait(
                        tasks, timeout=self._keepalive_seconds,
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                finally:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)

                completed = tuple(
                    task for task in tasks if task.done() and not task.cancelled()
                )
                if not completed:
                    yield ": keepalive\n\n"
                    continue

                for task in completed:
                    subscription = tasks[task]
                    yield _sse(subscription.event_type, _payload(subscription.event_type, task.result()))
        finally:
            for subscription in subscriptions:
                subscription.unsubscribe(subscription.queue)

    def _subscribe(self) -> tuple[_Subscription, ...]:
        authorization_queue = self._authorization_requests.subscribe()
        try:
            confirmation_queue = self._workflow_confirmations.subscribe()
        except Exception:
            self._authorization_requests.unsubscribe(authorization_queue)
            raise
        try:
            workflow_queue = self._workflow_events.subscribe()
        except Exception:
            self._workflow_confirmations.unsubscribe(confirmation_queue)
            self._authorization_requests.unsubscribe(authorization_queue)
            raise
        return (
            _Subscription(
                "authorization_requests_changed",
                authorization_queue,
                self._authorization_requests.unsubscribe,
            ),
            _Subscription(
                "workflow_confirmations_changed",
                confirmation_queue,
                self._workflow_confirmations.unsubscribe,
            ),
            _Subscription("workflow_execution", workflow_queue, self._workflow_events.unsubscribe),
        )


def _payload(event_type: str, event: object) -> dict[str, object]:
    if event_type != "workflow_execution":
        return {}
    if not isinstance(event, WorkflowExecutionEvent):
        raise TypeError("Workflow event manager emitted an invalid event.")
    return {
        "workflow_execution_id": event.id,
        "state": event.state,
        "progress_content": event.progress_content,
    }


def _sse(event_type: str, data: dict[str, object]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
