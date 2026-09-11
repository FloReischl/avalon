from typing import Protocol


class Command(Protocol):
    key: str

    def execute(self, payload: str) -> str:
        ...
