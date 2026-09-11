from typing import Protocol


class Command(Protocol):
    key: str

    async def execute(self, payload: str) -> str:
        ...
