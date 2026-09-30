"""In-process live invalidation for persisted workflow executions."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowExecutionEvent:
    id: int
    state: str
    progress_content: list[str] | None


class WorkflowEventManager:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[WorkflowExecutionEvent]] = set()

    def subscribe(self) -> asyncio.Queue[WorkflowExecutionEvent]:
        queue: asyncio.Queue[WorkflowExecutionEvent] = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[WorkflowExecutionEvent]) -> None:
        self._subscribers.discard(queue)

    def publish(self, event: WorkflowExecutionEvent) -> None:
        for queue in tuple(self._subscribers):
            queue.put_nowait(event)


_manager = WorkflowEventManager()


def get_workflow_event_manager() -> WorkflowEventManager:
    return _manager
