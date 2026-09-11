from app.runtime.ollama import OllamaRuntime
from app.state import AvaloState

from .avatar import AvatarCommand
from .llm import LlmCommand
from .registry import CommandRegistry


def build_command_registry(state: AvaloState) -> CommandRegistry:
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