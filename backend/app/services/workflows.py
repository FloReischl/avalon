"""Out-of-process execution of registered workflows."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import secrets
import sys

from pydantic import JsonValue

from app.workflows_config import WorkflowsConfig, get_workflows_config
from app.persistence.database import create_database_engine, create_session_factory
from app.persistence.workflow_execution_repository import WorkflowExecutionRepository
from app.services.workflow_events import WorkflowExecutionEvent, get_workflow_event_manager


logger = logging.getLogger(__name__)


class WorkflowExecutionError(RuntimeError):
    """A registered workflow ended unsuccessfully."""


class WorkflowService:
    """Resolve server-owned workflow keys and execute them safely."""

    def __init__(self, config: WorkflowsConfig | None = None, repository: WorkflowExecutionRepository | None = None) -> None:
        self._config = config
        self._repository = repository

    def _repository_for_call(self) -> tuple[WorkflowExecutionRepository, object | None]:
        if self._repository is not None:
            return self._repository, None
        engine = create_database_engine()
        return WorkflowExecutionRepository(create_session_factory(engine)), engine

    async def execute(self, workflow_key: str, payload: JsonValue, chat_id: int, backend_url: str, principal_id: int | None = None) -> int:
        config = self._config or get_workflows_config()
        try:
            workflow = config.get(workflow_key)
        except KeyError as exc:
            raise WorkflowExecutionError(f"Unknown workflow: {workflow_key}") from exc

        repository, engine = self._repository_for_call()
        if principal_id is not None and not repository.chat_matches_principal(chat_id, principal_id):
            if engine is not None:
                engine.dispose()
            raise WorkflowExecutionError("Workflow execution context does not belong to principal.")
        token = secrets.token_urlsafe(32)
        execution = repository.create(chat_id, hashlib.sha256(token.encode()).hexdigest())
        self._publish(execution)
        envelope = {"avalon": {"workflow_execution_id": execution.id, "backend_url": backend_url, "runtime_token": token}, "payload": payload}
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, str(workflow.file_path), stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            assert process.stdin is not None
            process.stdin.write(json.dumps(envelope, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            await process.stdin.drain()
            process.stdin.close()
            asyncio.create_task(self._monitor(process, execution.id, workflow_key, repository, engine))
            return execution.id
        except Exception as exc:
            updated = repository.append_process_failure(
                execution.id, f"Workflow failed to start: {exc}"
            )
            if updated is not None:
                self._publish(updated)
            if engine is not None:
                engine.dispose()
            raise

    async def _monitor(self, process, execution_id: int, workflow_key: str, repository: WorkflowExecutionRepository, engine: object | None) -> None:
        try:
            stdout, stderr = await process.communicate()
            current = repository.get(execution_id)
            if current is None or current.state != "running":
                return
            if process.returncode == 0:
                updated = repository.update(execution_id, state="completed", progress_content=None, has_progress=False)
            else:
                detail = f"Workflow failed (exit code {process.returncode})"
                logger.error("workflow=%s exit_code=%s stdout=%r stderr=%r", workflow_key, process.returncode, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace"))
                updated = repository.append_process_failure(execution_id, detail)
            if updated is not None:
                self._publish(updated)
        finally:
            if engine is not None:
                engine.dispose()

    @staticmethod
    def _publish(execution) -> None:
        get_workflow_event_manager().publish(WorkflowExecutionEvent(execution.id, execution.state, json.loads(execution.progress_content) if execution.progress_content else None))
