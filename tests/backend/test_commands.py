import logging

import pytest

from app.commands import CommandContext, CommandRegistry, CommandRequest, parse_command



class StubCommand:
    key = "test"

    def __init__(self, response: str = "ok") -> None:
        self.response = response
        self.payloads: list[str] = []

    async def execute(
        self,
        payload: str,
        context: CommandContext | None = None,
    ) -> str:
        del context
        self.payloads.append(payload)
        return self.response



def test_parse_command_returns_first_identifier_and_remaining_text():
    assert parse_command("/avatar set standard") == CommandRequest(
        key="avatar",
        payload="set standard",
    )


def test_parse_command_accepts_single_identifier_without_payload():
    assert parse_command("/help") == CommandRequest(
        key="help",
        payload="",
    )


def test_parse_command_ignores_leading_and_duplicate_separator_whitespace():
    assert parse_command("  /foo   bar   hello   world") == CommandRequest(
        key="foo",
        payload="bar   hello   world",
    )


def test_parse_command_is_case_insensitive():
    assert parse_command("/AvAtAr SeT standard") == CommandRequest(
        key="AvAtAr",
        payload="SeT standard",
    )


def test_parse_command_accepts_identifier_characters():
    assert parse_command("/foo_2-bar baz_3-qux payload") == CommandRequest(
        key="foo_2-bar",
        payload="baz_3-qux payload",
    )


def test_parse_command_rejects_non_slash_prefix():
    assert parse_command("avatar set standard") is None


def test_parse_command_rejects_invalid_first_identifier():
    assert parse_command("/avatar! set standard") is None


def test_registry_matches_single_part_key():
    command = StubCommand()
    registry = CommandRegistry()
    registry.register(command)

    request = parse_command("/test hello")

    assert request is not None
    assert registry.match(request) == CommandRequest(
        key="test",
        payload="hello",
    )


def test_registry_matches_multi_part_key_and_preserves_payload():
    class MultiPartCommand(StubCommand):
        key = "foo bar"

    registry = CommandRegistry()
    registry.register(MultiPartCommand())

    request = parse_command("/foo   bar hello   world")

    assert request is not None
    assert registry.match(request) == CommandRequest(
        key="foo bar",
        payload="hello   world",
    )


def test_registry_matches_multi_part_key_without_payload():
    class MultiPartCommand(StubCommand):
        key = "foo bar"

    registry = CommandRegistry()
    registry.register(MultiPartCommand())

    request = parse_command("/foo bar")

    assert request is not None
    assert registry.match(request) == CommandRequest(
        key="foo bar",
        payload="",
    )


def test_registry_normalizes_whitespace_between_identifier_parts():
    class MultiPartCommand(StubCommand):
        key = "foo bar"

    registry = CommandRegistry()
    registry.register(MultiPartCommand())

    request = parse_command("/foo    bar payload")

    assert request is not None
    assert registry.match(request) == CommandRequest(
        key="foo bar",
        payload="payload",
    )


def test_registry_does_not_match_identifier_prefix():
    class HelpCommand(StubCommand):
        key = "help"

    registry = CommandRegistry()
    registry.register(HelpCommand())

    request = parse_command("/helpful")

    assert request is not None
    assert registry.match(request) is None


def test_registry_uses_longest_matching_key():
    class HelpCommand(StubCommand):
        key = "help"

    class LlmHelpCommand(StubCommand):
        key = "help llm"

    registry = CommandRegistry()
    registry.register(HelpCommand())
    registry.register(LlmHelpCommand())

    request = parse_command("/help llm set")

    assert request is not None
    assert registry.match(request) == CommandRequest(
        key="help llm",
        payload="set",
    )


def test_registry_returns_none_for_unknown_command():
    registry = CommandRegistry()

    request = parse_command("/missing payload")

    assert request is not None
    assert registry.match(request) is None


def test_registry_reports_registered_command():
    command = StubCommand()
    registry = CommandRegistry()
    registry.register(command)

    assert registry.contains(CommandRequest(key="test", payload="hello"))
    assert not registry.contains(CommandRequest(key="missing", payload="hello"))


@pytest.mark.asyncio
async def test_registry_executes_registered_command():
    command = StubCommand(response="done")
    registry = CommandRegistry()
    registry.register(command)

    response = await registry.execute(
        CommandRequest(key="test", payload="hello")
    )

    assert response == "done"
    assert command.payloads == ["hello"]


@pytest.mark.asyncio
async def test_registry_lookup_is_case_insensitive():
    command = StubCommand()
    registry = CommandRegistry()
    registry.register(command)

    assert (
        await registry.execute(CommandRequest(key="TEST", payload=""))
        == "ok"
    )


def test_registry_rejects_duplicate_keys_case_insensitively():
    class DuplicateCommand(StubCommand):
        key = "TEST"

    registry = CommandRegistry()
    registry.register(StubCommand())

    with pytest.raises(ValueError, match="duplicate command key"):
        registry.register(DuplicateCommand())


@pytest.mark.asyncio
async def test_registry_reports_unknown_command():
    registry = CommandRegistry()

    assert (
        await registry.execute(
            CommandRequest(key="foobar", payload="test")
        )
        == "unknown command: foobar"
    )


@pytest.mark.asyncio
async def test_registry_reports_missing_identifier():
    registry = CommandRegistry()

    assert (
        await registry.execute(CommandRequest(key="", payload=""))
        == "missing command identifier"
    )


@pytest.mark.asyncio
async def test_registry_logs_command_failure_and_returns_error_message(caplog):
    class FailingCommand:
        key = "fail"

        async def execute(
            self,
            payload: str,
            context: CommandContext | None = None,
        ) -> str:
            del payload, context
            raise RuntimeError("kaputt")

    registry = CommandRegistry()
    registry.register(FailingCommand())

    with caplog.at_level(logging.ERROR):
        response = await registry.execute(
            CommandRequest(key="fail", payload="")
        )

    assert response == "command failed!\n\nmessage: kaputt"
    assert "Command 'fail' failed" in caplog.text
    assert "RuntimeError: kaputt" in caplog.text
