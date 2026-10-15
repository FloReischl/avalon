"""Local persistence setup for debugging registered workflows."""

from pathlib import Path

from sqlalchemy import select

from app.agents_config import load_agents_config
from app.persistence.database import create_database_engine, create_session_factory
from app.persistence.models import Agent, Chat, ProgressMessage, WorkflowExecution
from app.workflows_config import load_workflows_config


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_CONFIG_PATH = PROJECT_ROOT / "data/blueprints/user.avalon/workflows.yaml"
AGENTS_CONFIG_PATH = PROJECT_ROOT / "data/blueprints/user.avalon/agents.yaml"


class WorkflowExecutionManager:
    """Create persisted workflow executions for local debugging."""

    def create_execution(
        self,
        chat_title: str,
        workflow_key: str,
        agent_name: str,
        invocation_id: str,
    ) -> int:
        workflows = load_workflows_config(WORKFLOWS_CONFIG_PATH)
        try:
            workflows.get(workflow_key)
        except KeyError as exc:
            raise KeyError(f"Unknown workflow: {workflow_key}") from exc

        agents = load_agents_config(AGENTS_CONFIG_PATH)
        configured_agent = next(
            (agent for agent in agents.agents if agent.name == agent_name), None
        )
        if configured_agent is None:
            raise KeyError(f"Agent '{agent_name}' not found.")

        engine = create_database_engine()
        factory = create_session_factory(engine)
        try:
            with factory.begin() as session:
                agent = session.scalar(
                    select(Agent).where(Agent.key == configured_agent.key)
                )
                if agent is None:
                    raise LookupError(f"Agent '{agent_name}' is not persisted.")

                chat = session.scalar(
                    select(Chat)
                    .where(Chat.title == chat_title)
                    .order_by(Chat.created_at.desc(), Chat.id.desc())
                )
                if chat is None:
                    raise LookupError(f"Chat '{chat_title}' not found.")
                if chat.agent_id != agent.id:
                    raise ValueError("Chat does not belong to agent.")

                progress_message = ProgressMessage(
                    chat_id=chat.id,
                    invocation_id=invocation_id,
                    seq=chat.next_message_seq,
                )
                chat.next_message_seq += 1
                execution = WorkflowExecution(
                    progress_message=progress_message,
                    workflow_key=workflow_key,
                    state="running",
                )
                session.add_all([progress_message, execution])
                session.flush()
                return execution.id
        finally:
            engine.dispose()
