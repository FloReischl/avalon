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
from app.persistence.chat_repository import ChatRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.persistence.workflow_execution_repository import WorkflowExecutionRepository
from app.services.context_compression import (
    build_current_datetime_context,
    build_model_context,
    parse_compressed_context,
)
from app.services.workflow_events import WorkflowExecutionEvent, get_workflow_event_manager
from app.state import get_avalon_state


logger = logging.getLogger(__name__)


class WorkflowExecutionError(RuntimeError):
    """A registered workflow ended unsuccessfully."""


class WorkflowService:
    """Resolve server-owned workflow keys and execute them safely."""

    def __init__(
        self,
        config: WorkflowsConfig | None = None,
        repository: WorkflowExecutionRepository | None = None,
        chat_repository: ChatRepository | None = None,
    ) -> None:
        self._config = config
        self._repository = repository
        self._chat_repository = chat_repository

    def _repositories_for_call(
        self,
    ) -> tuple[WorkflowExecutionRepository, ChatRepository, object | None]:
        if self._repository is not None and self._chat_repository is not None:
            return self._repository, self._chat_repository, None
        if self._repository is not None or self._chat_repository is not None:
            raise RuntimeError(
                "WorkflowService requires both repositories when dependencies are injected."
            )
        engine = create_database_engine()
        factory = create_session_factory(engine)
        return WorkflowExecutionRepository(factory), ChatRepository(factory), engine

    def _context_identity(self, chat_repository: ChatRepository, agent_id: int | None):
        state = get_avalon_state()

        if agent_id is None:
            return state.current_avatar

        persisted_agent = chat_repository.get_agent_by_id(agent_id)
        if persisted_agent is None:
            raise WorkflowExecutionError(f"Agent {agent_id} does not exist.")

        configured_agent = state.get_agent(persisted_agent.key)
        if configured_agent is None:
            raise WorkflowExecutionError(
                f"Agent '{persisted_agent.key}' is not configured."
            )
        return configured_agent

    async def execute(self, workflow_key: str, payload: JsonValue, chat_id: int, invocation_id: str, backend_url: str, principal_id: int | None = None) -> int:
        config = self._config or get_workflows_config()
        try:
            workflow = config.get(workflow_key)
        except KeyError as exc:
            raise WorkflowExecutionError(f"Unknown workflow: {workflow_key}") from exc

        repository, chat_repository, engine = self._repositories_for_call()
        if principal_id is not None and not repository.chat_matches_principal(chat_id, principal_id):
            if engine is not None:
                engine.dispose()
            raise WorkflowExecutionError("Workflow execution context does not belong to principal.")

        chat = chat_repository.get_chat(chat_id)
        if chat is None:
            if engine is not None:
                engine.dispose()
            raise WorkflowExecutionError(f"Chat {chat_id} does not exist.")

        identity = self._context_identity(chat_repository, chat.agent_id)
        model_context = build_model_context(
            chat_repository.get_text_messages(chat_id),
            parse_compressed_context(chat.compressed_context),
            chat.compressed_through_seq,
        )

        token = secrets.token_urlsafe(32)
        execution = repository.create(
            chat_id, invocation_id, workflow_key,
            hashlib.sha256(token.encode()).hexdigest(),
        )
        self._publish(execution)
        envelope = {
            "avalon": {
                "workflow_execution_id": execution.id,
                "backend_url": backend_url,
                "runtime_token": token,
                "model_persona": "" if identity is None else identity.persona,
                "model_instructions": "" if identity is None else identity.instructions,
                "model_context": model_context,
                "current_datetime": build_current_datetime_context(),
            },
            "payload": payload,
        }
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
        get_workflow_event_manager().publish(
            WorkflowExecutionEvent(
                execution.id,
                execution.state,
                json.loads(execution.progress_message.messages),
            )
        )
