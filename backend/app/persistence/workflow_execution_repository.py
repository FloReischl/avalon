"""Persistence operations for workflow lifecycle state."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, sessionmaker

from app.persistence.models import (
    Agent, Chat, Message, ProgressMessage, WorkflowExecution,
)

TERMINAL_STATES = frozenset({"completed", "failed", "aborted"})
VALID_STATES = frozenset({"running", "pending", *TERMINAL_STATES})


class WorkflowExecutionRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(
        self, chat_id: int, invocation_id: str, workflow_key: str, token_hash: str
    ) -> WorkflowExecution:
        """Create one stable progress element and its running execution atomically."""
        with self._session_factory.begin() as session:
            chat = session.get(Chat, chat_id)
            if chat is None:
                raise ValueError(f"Chat {chat_id} does not exist.")
            message = ProgressMessage(
                chat_id=chat_id,
                invocation_id=invocation_id,
                seq=chat.next_message_seq,
            )
            chat.next_message_seq += 1
            execution = WorkflowExecution(
                progress_message=message,
                workflow_key=workflow_key,
                state="running",
                runtime_token_hash=token_hash,
            )
            session.add_all([message, execution])
            session.flush()
            execution_id = execution.id
        loaded = self.get(execution_id)
        assert loaded is not None
        return loaded

    def get(self, execution_id: int) -> WorkflowExecution | None:
        with self._session_factory() as session:
            return session.scalar(
                select(WorkflowExecution)
                .where(WorkflowExecution.id == execution_id)
                .options(
                    joinedload(WorkflowExecution.progress_message).joinedload(
                        ProgressMessage.workflow_execution
                    )
                )
            )

    def chat_matches_principal(self, chat_id: int, principal_id: int) -> bool:
        with self._session_factory() as session:
            chat = session.get(Chat, chat_id)
            if chat is None:
                return False
            if chat.principal_id is not None:
                return chat.principal_id == principal_id
            agent = session.get(Agent, chat.agent_id) if chat.agent_id is not None else None
            return agent is not None and agent.principal_id == principal_id

    def update(self, execution_id: int, *, state: str | None, progress_content: list[str] | None, has_progress: bool) -> WorkflowExecution | None:
        """Apply one validated snapshot update; return None when it was identical."""
        with self._session_factory.begin() as session:
            execution = session.scalar(
                select(WorkflowExecution)
                .where(WorkflowExecution.id == execution_id)
                .options(joinedload(WorkflowExecution.progress_message))
            )
            if execution is None:
                raise LookupError("Workflow execution does not exist.")
            if execution.state in TERMINAL_STATES:
                raise ValueError("Workflow execution is terminal.")
            if state is not None and state not in VALID_STATES:
                raise ValueError("Invalid workflow state.")
            if has_progress and progress_content is None:
                raise ValueError("Workflow progress cannot be reset to null.")
            serialized = (
                json.dumps(progress_content, ensure_ascii=False)
                if has_progress else execution.progress_message.messages
            )
            next_state = state or execution.state
            if serialized == execution.progress_message.messages and next_state == execution.state:
                return None
            execution.progress_message.messages = serialized
            execution.state = next_state
            execution.updated_at = datetime.now()
            session.flush()
            session.refresh(execution)
            return execution

    def append_process_failure(self, execution_id: int, detail: str) -> WorkflowExecution | None:
        execution = self.get(execution_id)
        if execution is None or execution.state in TERMINAL_STATES:
            return None
        progress = json.loads(execution.progress_message.messages)
        progress.append(detail)
        return self.update(execution_id, state="failed", progress_content=progress, has_progress=True)
