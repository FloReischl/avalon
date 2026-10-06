from app.agents_config import AgentConfig
from app.persistence.chat_repository import ChatRepository
from app.user_config import get_user_config

from .base import CommandContext


class AgentInviteCommand:
    """Assign one configured agent to the current chat."""

    key = "agent_invite"

    def __init__(
        self,
        repository: ChatRepository,
        agents: tuple[AgentConfig, ...],
    ) -> None:
        self._repository = repository
        self._agents = agents

    async def execute(
        self,
        payload: str,
        context: CommandContext | None = None,
    ) -> str:
        if context is None:
            raise RuntimeError("Agent invite requires a chat context.")

        selector, force = self._parse_payload(payload)
        target = self._resolve_agent(selector)
        if target is None:
            return "Unknown agent"

        chat = self._repository.get_chat(context.chat_id)
        if chat is None:
            raise RuntimeError(f"Chat {context.chat_id} does not exist.")

        if chat.agent_id is not None:
            current = self._repository.get_agent_by_id(chat.agent_id)
            current_name = current.key if current is not None else "unknown"
            if current is not None:
                configured = self._configured_agent(current.key)
                if configured is not None:
                    current_name = configured.name
            if not force:
                return (
                    f"Agent {current_name} already in chat. "
                    "use '-force' to overwrite"
                )

        persisted = self._repository.get_agent_by_key(target.key)
        if persisted is None:
            raise RuntimeError(
                f"Configured agent '{target.key}' was not reconciled."
            )

        if not self._repository.assign_agent(context.chat_id, persisted.id):
            raise RuntimeError(f"Chat {context.chat_id} does not exist.")

        return f"Agent {target.name} invited."

    def _resolve_agent(self, selector: str) -> AgentConfig | None:
        if not selector:
            return None

        normalized = selector.casefold()

        exact_key = next(
            (
                agent
                for agent in self._agents
                if agent.key.casefold() == normalized
            ),
            None,
        )
        if exact_key is not None:
            return exact_key

        matches = [
            agent
            for agent in self._agents
            if agent.name.casefold().startswith(normalized)
        ]
        if len(matches) > 1:
            raise ValueError("Ambiguous agent name")
        if not matches:
            return None
        return matches[0]

    def _configured_agent(self, key: str) -> AgentConfig | None:
        normalized = key.casefold()
        return next(
            (
                agent
                for agent in self._agents
                if agent.key.casefold() == normalized
            ),
            None,
        )

    @staticmethod
    def _parse_payload(payload: str) -> tuple[str, bool]:
        stripped = payload.strip()
        force = stripped.casefold().endswith(" -force")
        if force:
            stripped = stripped[:-7].rstrip()
        return stripped, force


class AgentUnloadCommand:
    """Remove the current agent and restore the normal chat identity."""

    key = "agent_unload"

    def __init__(
        self,
        repository: ChatRepository,
        agents: tuple[AgentConfig, ...],
    ) -> None:
        self._repository = repository
        self._agents = agents

    async def execute(
        self,
        payload: str,
        context: CommandContext | None = None,
    ) -> str:
        del payload

        if context is None:
            raise RuntimeError("Agent unload requires a chat context.")

        chat = self._repository.get_chat(context.chat_id)
        if chat is None:
            raise RuntimeError(f"Chat {context.chat_id} does not exist.")
        if chat.agent_id is None:
            return "No agent in chat."

        persisted_agent = self._repository.get_agent_by_id(chat.agent_id)
        agent_name = "unknown"
        if persisted_agent is not None:
            configured = next(
                (
                    agent
                    for agent in self._agents
                    if agent.key.casefold() == persisted_agent.key.casefold()
                ),
                None,
            )
            agent_name = (
                configured.name
                if configured is not None
                else persisted_agent.key
            )

        if not self._repository.unload_agent(context.chat_id):
            raise RuntimeError(f"Chat {context.chat_id} does not exist.")

        return f"Agent {agent_name} unloaded."
