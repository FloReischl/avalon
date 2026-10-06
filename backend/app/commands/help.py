from .base import CommandContext
from .registry import CommandRegistry


class HelpCommand:
    """Show help text supplied by registered commands."""

    key = "help"

    def __init__(self, registry: CommandRegistry) -> None:
        self._registry = registry

    def get_help(self) -> str:
        return (
            "/help [command]\n\n"
            "Shows help for available commands.\n\n"
            "Without a command, shows help for all commands.\n"
            "A command prefix shows all matching commands."
        )

    async def execute(
        self,
        payload: str,
        context: CommandContext | None = None,
    ) -> str:
        del context

        query = self._normalize_query(payload)
        matches = [
            (self._registry.normalize_key(command.key), command)
            for command in self._registry.commands()
        ]
        if query:
            matches = [
                (key, command)
                for key, command in matches
                if key == query or key.startswith(f"{query} ")
            ]

        matches.sort(key=lambda match: match[0])
        if not matches:
            return f"No commands found for: {query}"

        return "\n\n".join(command.get_help() for _, command in matches)

    @staticmethod
    def _normalize_query(payload: str) -> str:
        normalized = " ".join(payload.split())
        if not normalized:
            return ""
        try:
            return CommandRegistry.normalize_key(normalized)
        except ValueError:
            return normalized.casefold()
