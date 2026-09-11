import logging

from .base import Command
from .parser import CommandRequest


logger = logging.getLogger(__name__)


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        key = command.key.lower()

        if key in self._commands:
            raise ValueError(f"duplicate command key: {command.key}")

        self._commands[key] = command

    def execute(self, request: CommandRequest) -> str:
        if not request.key:
            return "missing command identifier"

        command = self._commands.get(request.key.lower())
        if command is None:
            return f"unknown command: {request.key}"

        try:
            return command.execute(request.payload)
        except Exception as exc:
            logger.exception("Command '%s' failed", request.key)
            return f"command failed!\n\nmessage: {exc}"
