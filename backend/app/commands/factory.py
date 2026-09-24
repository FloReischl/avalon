from app.runtime.ollama import OllamaRuntime
from app.state import AvalonState

from .avatar_set import AvatarCommand
from .llm_set import LlmCommand
from .registry import CommandRegistry


def build_command_registry(state: AvalonState) -> CommandRegistry:
    """Build the process command set against the current runtime state."""
    registry = CommandRegistry()
    registry.register(AvatarCommand(state))
    registry.register(
        LlmCommand(
            state,
            OllamaRuntime(lambda: state),
        )
    )
    return registry