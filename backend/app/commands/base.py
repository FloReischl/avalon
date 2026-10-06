from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CommandContext:
    chat_id: int


class Command(Protocol):
    key: str

    def get_help(self) -> str:
        """Return the human-readable help text for this command."""
        ...

    async def execute(
        self,
        payload: str,
        context: CommandContext | None = None,
    ) -> str:
        ...
