import logging

import pytest

from app.commands import CommandRegistry, CommandRequest, parse_command


class StubCommand:
    key = "test"

    def __init__(self, response: str = "ok") -> None:
        self.response = response
        self.payloads: list[str] = []

    async def execute(self, payload: str) -> str:
        self.payloads.append(payload)
        return self.response


def test_parse_command_with_payload():
    assert parse_command("/command avatar standard") == CommandRequest(
        key="avatar",
        payload="standard",
    )


def test_parse_command_without_payload():
    assert parse_command("/command jodel") == CommandRequest(
        key="jodel",
        payload="",
    )


def test_parse_command_ignores_leading_and_duplicate_separator_whitespace():
    assert parse_command("  /command   foo   hello   world") == CommandRequest(
        key="foo",
        payload="hello   world",
    )


def test_parse_command_is_case_insensitive():
    assert parse_command("/COMMAND AvAtAr standard") == CommandRequest(
        key="avatar",
        payload="standard",
    )


def test_parse_command_accepts_identifier_characters():
    assert parse_command("/command foo_2-bar payload") == CommandRequest(
        key="foo_2-bar",
        payload="payload",
    )


def test_parse_command_rejects_non_command_prefix():
    assert parse_command("/commandx foo") is None


def test_parse_command_without_identifier():
    assert parse_command("/command   ") == CommandRequest(key="", payload="")


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

        async def execute(self, payload: str) -> str:
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