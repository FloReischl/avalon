from app.persistence.chat_repository import ChatRepository
from app.runtime.ollama import OllamaRuntime
from app.state import AvalonState

from .agent import AgentInviteCommand, AgentUnloadCommand
from .avatar_set import AvatarCommand
from .llm_set import LlmCommand
from .registry import CommandRegistry


def build_command_registry(
    state: AvalonState,
    repository: ChatRepository | None = None,
) -> CommandRegistry:

    """Build the process command set against the current runtime state."""
    registry = CommandRegistry()
    registry.register(AvatarCommand(state))
    registry.register(
        LlmCommand(
            state,
            OllamaRuntime(lambda: state),
        )
    )
    if repository is not None:
        registry.register(AgentInviteCommand(repository, state.agents))
        registry.register(AgentUnloadCommand(repository, state.agents))
    return registry

