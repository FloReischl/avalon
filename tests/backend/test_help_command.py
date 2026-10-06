from types import SimpleNamespace

import pytest

from app.commands import CommandContext, CommandRegistry, parse_command
from app.commands.factory import build_command_registry
from app.commands.help import HelpCommand


class StubCommand:
    def __init__(self, key: str) -> None:
        self.key = key
        self.help_calls = 0

    def get_help(self) -> str:
        self.help_calls += 1
        return f"help: {self.key}"

    async def execute(
        self,
        payload: str,
        context: CommandContext | None = None,
    ) -> str:
        del payload, context
        return "ok"


def registry_with_help(*keys: str) -> tuple[CommandRegistry, list[StubCommand]]:
    registry = CommandRegistry()
    commands = [StubCommand(key) for key in keys]
    for command in commands:
        registry.register(command)
    registry.register(HelpCommand(registry))
    return registry, commands


@pytest.mark.asyncio
async def test_help_lists_all_commands_in_normalized_key_order_including_itself():
    registry, _ = registry_with_help("llm set", "agent unload", "agent invite")

    response = await registry.execute(parse_command("/help"))  # type: ignore[arg-type]

    assert response == "\n\n".join(
        (
            "help: agent invite",
            "help: agent unload",
            HelpCommand(registry).get_help(),
            "help: llm set",
        )
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "expected"),
    (
        ("agent", ("help: agent invite", "help: agent unload")),
        ("agent invite", ("help: agent invite",)),
        ("llm", ("help: llm set",)),
        ("llm set", ("help: llm set",)),
        ("LLM SET", ("help: llm set",)),
        ("  llm   set  ", ("help: llm set",)),
    ),
)
async def test_help_matches_complete_key_prefixes_and_normalizes_query(
    payload: str,
    expected: tuple[str, ...],
):
    registry, _ = registry_with_help("llm set", "agent unload", "agent invite")

    response = await registry.execute(
        parse_command(f"/help {payload}")  # type: ignore[arg-type]
    )

    assert response == "\n\n".join(expected)


@pytest.mark.asyncio
async def test_help_treats_whitespace_only_payload_as_help_for_all_commands():
    registry, _ = registry_with_help("llm set", "agent unload", "agent invite")

    response = await registry.execute(parse_command("/help    "))  # type: ignore[arg-type]

    assert response == "\n\n".join(
        (
            "help: agent invite",
            "help: agent unload",
            HelpCommand(registry).get_help(),
            "help: llm set",
        )
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", ("ll", "agent i", "unknown"))
async def test_help_rejects_character_prefixes_and_reports_no_match(payload: str):
    registry, commands = registry_with_help("llm set", "agent invite")

    response = await registry.execute(parse_command(f"/help {payload}"))  # type: ignore[arg-type]

    assert response == f"No commands found for: {payload}"
    assert all(command.help_calls == 0 for command in commands)


@pytest.mark.asyncio
async def test_help_finds_its_own_help():
    registry, _ = registry_with_help("llm set")

    response = await registry.execute(parse_command("/help help"))  # type: ignore[arg-type]

    assert response == HelpCommand(registry).get_help()


@pytest.mark.asyncio
async def test_help_handles_an_empty_registry():
    registry = CommandRegistry()
    command = HelpCommand(registry)

    assert await command.execute("") == "No commands found for: "


@pytest.mark.asyncio
async def test_factory_registers_help_for_the_normal_command_path():
    state = SimpleNamespace(avatars=(), llms=())
    registry = build_command_registry(state)  # type: ignore[arg-type]
    request = parse_command("/help llm")

    assert request is not None
    matched = registry.match(request)
    assert matched is not None
    assert matched.key == "help"
    assert await registry.execute(matched) == (
        "/llm set <llm>\n\n"
        "Changes the active LLM.\n\n"
        "Available LLMs:\n  (none)"
    )
