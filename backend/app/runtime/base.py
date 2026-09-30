"""Runtime-independent text model contracts."""

from collections.abc import AsyncIterator
from typing import Protocol


class ModelRuntime(Protocol):
    """Contract implemented by a local text-generation runtime."""

    async def health(self) -> bool:
        ...

    async def warm_up(self) -> None:
        ...

    async def generate_text(self, message: str) -> str:
        ...

    async def generate_text_messages(
        self,
        messages: list[dict[str, str]],
    ) -> str:
        ...

    def generate_text_stream(
        self,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        ...
