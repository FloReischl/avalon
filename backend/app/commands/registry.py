import logging
import re

from .base import Command, CommandContext
from .parser import CommandRequest



logger = logging.getLogger(__name__)


_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        key = self._normalize_key(command.key)

        if key in self._commands:
            raise ValueError(f"duplicate command key: {command.key}")

        self._commands[key] = command

    def match(self, request: CommandRequest) -> CommandRequest | None:
        """Resolve a parsed invocation to its longest registered key."""
        for key in sorted(
            self._commands,
            key=lambda candidate: len(candidate.split()),
            reverse=True,
        ):
            key_parts = key.split()
            if request.key.lower() != key_parts[0]:
                continue

            remainder = request.payload
            matched = True
            for part in key_parts[1:]:
                token = re.match(r"(\S+)(?:\s+|$)", remainder)
                if token is None or token.group(1).lower() != part:
                    matched = False
                    break
                remainder = remainder[token.end() :]

            if matched:
                return CommandRequest(key=key, payload=remainder.lstrip())

        return None

    def contains(self, request: CommandRequest) -> bool:
        return request.key.lower() in self._commands

    async def execute(
        self,
        request: CommandRequest,
        context: CommandContext | None = None,
    ) -> str:
        if not request.key:
            return "missing command identifier"

        command = self._commands.get(request.key.lower())
        if command is None:
            return f"unknown command: {request.key}"

        try:
            return await command.execute(request.payload, context)
        except Exception as exc:

            logger.exception("Command '%s' failed", request.key)
            return f"command failed!\n\nmessage: {exc}"

    @staticmethod
    def _normalize_key(key: str) -> str:
        parts = key.split()
        if not parts or any(
            not _IDENTIFIER_PATTERN.fullmatch(part) for part in parts
        ):
            raise ValueError(f"invalid command key: {key}")
        return " ".join(part.lower() for part in parts)
