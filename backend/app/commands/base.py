from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CommandContext:
    chat_id: int


class Command(Protocol):
    key: str

    async def execute(
        self,
        payload: str,
        context: CommandContext | None = None,
    ) -> str:
        ...

