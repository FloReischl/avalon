"""Tests for the persistent text-chat application service."""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.commands import CommandContext, CommandRegistry

from app.persistence.chat_repository import ChatRepository
from app.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from app.persistence.migrations import run_migrations
from app.services.chat import (
    ChatCompressionFailedError,
    ChatNotFoundError,
    ChatService,
)


DEFAULT_AGENT = SimpleNamespace(
    key="default",
    persona="Du bist Frieda.",
    instructions="Antworte kurz.",
)


class FakeRuntime:
    def __init__(self, chunks: list[str] | None = None) -> None:
        self.chunks = chunks or ["Hallo ", "Flo"]
        self.messages: list[dict[str, str]] | None = None
        self.calls: list[list[dict[str, str]]] = []

    async def generate_text_stream(
        self,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        self.messages = messages
        self.calls.append(messages)
        for chunk in self.chunks:
            yield chunk


def assert_runtime_context(
    messages: list[dict[str, str]],
    expected_context: list[dict[str, str]],
    identity=DEFAULT_AGENT,
) -> None:
    assert messages[0]["role"] == "system"
    assert messages[0]["content"].startswith("Aktuelles Datum und Uhrzeit: ")
    assert "Aktueller Ort: München, Deutschland" in messages[0]["content"]
    assert messages[1:] == [
        {
            "role": "system",
            "content": f"{identity.persona}\n\n{identity.instructions}",
        },
        *expected_context,
    ]


@pytest.fixture
def service(tmp_path: Path):
    path = tmp_path / "avalon.sqlite"
    run_migrations(path)
    engine = create_database_engine(path)
    repository = ChatRepository(create_session_factory(engine))
    runtime = FakeRuntime()

    try:
        yield ChatService(runtime, repository, agents=(DEFAULT_AGENT,)), repository, runtime
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_new_turn_persists_user_and_complete_assistant(service) -> None:
    chat_service, repository, runtime = service

    turn = chat_service.start_turn(None, "Hallo")
    chunks = [chunk async for chunk in chat_service.stream_response(turn)]

    assert chunks == ["Hallo ", "Flo"]
    assert runtime.messages is not None
    assert_runtime_context(
        runtime.messages, [{"role": "user", "content": "Hallo"}]
    )

    messages = repository.get_messages(turn.chat_id)
    assert [(message.role, message.content) for message in messages] == [
        ("user", "Hallo"),
        ("assistant", "Hallo Flo"),
    ]


@pytest.mark.asyncio
async def test_command_turn_persists_request_and_response_without_runtime(
    service,
) -> None:
    _, repository, runtime = service

    class EchoCommand:
        key = "test_echo"

        async def execute(
            self,
            payload: str,
            context: CommandContext | None = None,
        ) -> str:
            assert context is not None
            assert context.chat_id > 0
            return f"echo: {payload}"

    registry = CommandRegistry()
    registry.register(EchoCommand())
    chat_service = ChatService(
        runtime,
        repository,
        command_registry=registry,
        agents=(DEFAULT_AGENT,),
    )

    turn = chat_service.start_turn(None, "/test echo hello   world")
    chunks = [chunk async for chunk in chat_service.stream_response(turn)]

    assert chunks == ["echo: hello   world"]
    assert runtime.calls == []

    messages = repository.get_messages(turn.chat_id)
    assert [(message.role, message.content) for message in messages] == [
        ("user", "/test echo hello   world"),
        ("assistant", "echo: hello   world"),
    ]


@pytest.mark.asyncio
async def test_unknown_slash_command_is_processed_by_runtime(service) -> None:
    chat_service, repository, runtime = service

    turn = chat_service.start_turn(None, "/avatar foo test")
    chunks = [chunk async for chunk in chat_service.stream_response(turn)]

    assert chunks == ["Hallo ", "Flo"]
    assert len(runtime.calls) == 1
    assert_runtime_context(runtime.calls[0], [{"role": "user", "content": "/avatar foo test"}])

    messages = repository.get_messages(turn.chat_id)
    assert [(message.role, message.content) for message in messages] == [
        ("user", "/avatar foo test"),
        ("assistant", "Hallo Flo"),
    ]


@pytest.mark.asyncio
async def test_incomplete_slash_command_is_processed_by_runtime(service) -> None:
    chat_service, repository, runtime = service

    turn = chat_service.start_turn(None, "/avatar")
    chunks = [chunk async for chunk in chat_service.stream_response(turn)]

    assert chunks == ["Hallo ", "Flo"]
    assert len(runtime.calls) == 1
    assert_runtime_context(runtime.calls[0], [{"role": "user", "content": "/avatar"}])

    messages = repository.get_messages(turn.chat_id)
    assert [(message.role, message.content) for message in messages] == [
        ("user", "/avatar"),
        ("assistant", "Hallo Flo"),
    ]


@pytest.mark.asyncio
async def test_default_agent_system_prompt_precedes_persisted_context(service) -> None:
    _, repository, runtime = service
    agent = SimpleNamespace(
        key="default",
        persona="Du bist Frieda.",
        instructions="Antworte kurz.",
    )
    chat_service = ChatService(
        runtime,
        repository,
        agents=(agent,),
    )

    turn = chat_service.start_turn(None, "Hallo")
    _ = [chunk async for chunk in chat_service.stream_response(turn)]

    assert runtime.messages is not None
    assert_runtime_context(
        runtime.messages,
        [{"role": "user", "content": "Hallo"}],
        agent,
    )

@pytest.mark.asyncio
async def test_existing_chat_is_continued_with_persisted_context(service) -> None:
    chat_service, repository, runtime = service
    chat = repository.create_chat_with_message("Chat", "user", "Erste Frage")
    repository.add_message(chat.id, "assistant", "Erste Antwort")

    turn = chat_service.start_turn(chat.id, "Zweite Frage")
    chunks = [chunk async for chunk in chat_service.stream_response(turn)]

    assert chunks == ["Hallo ", "Flo"]
    assert_runtime_context(
        runtime.calls[0],
        [
            {"role": "user", "content": "Erste Frage"},
            {"role": "assistant", "content": "Erste Antwort"},
            {"role": "user", "content": "Zweite Frage"},
        ],
    )


@pytest.mark.asyncio
async def test_auto_title_is_generated_after_second_roundtrip(service) -> None:
    chat_service, repository, runtime = service
    chat = repository.create_chat_with_message("New Chat", "user", "Hallo")
    repository.add_message(chat.id, "assistant", "Hallo Flo")

    runtime.chunks = ["Persistenz", " mit SQLite"]

    turn = chat_service.start_turn(chat.id, "Wie speichern wir Chats?")
    _ = [chunk async for chunk in chat_service.stream_response(turn)]

    assert len(runtime.calls) == 1

    await chat_service.finalize_turn(turn)

    loaded = repository.get_chat(chat.id)
    assert loaded is not None
    assert loaded.title == "Persistenz mit SQLite"
    assert loaded.auto_title_attempted is True
    assert len(runtime.calls) == 2


@pytest.mark.asyncio
async def test_finalize_schedules_compression_without_waiting_for_it(service) -> None:
    chat_service, repository, runtime = service
    started = asyncio.Event()
    release = asyncio.Event()

    class BlockingCompression:
        async def compress_if_needed(self, chat_id: int) -> None:
            assert chat_id > 0
            started.set()
            await release.wait()

    chat_service = ChatService(
        runtime,
        repository,
        compression_service=BlockingCompression(),  # type: ignore[arg-type]
        agents=(DEFAULT_AGENT,),
    )
    turn = chat_service.start_turn(None, "Hallo")
    _ = [chunk async for chunk in chat_service.stream_response(turn)]

    await chat_service.finalize_turn(turn)
    await asyncio.wait_for(started.wait(), timeout=0.1)
    release.set()


@pytest.mark.asyncio
async def test_manual_title_prevents_auto_title_generation(service) -> None:
    chat_service, repository, runtime = service
    chat = repository.create_chat_with_message("New Chat", "user", "Hallo")
    repository.add_message(chat.id, "assistant", "Hallo Flo")
    repository.rename_chat(chat.id, "Mein Titel")

    turn = chat_service.start_turn(chat.id, "Zweite Frage")
    _ = [chunk async for chunk in chat_service.stream_response(turn)]
    await chat_service.finalize_turn(turn)

    loaded = repository.get_chat(chat.id)
    assert loaded is not None
    assert loaded.title == "Mein Titel"
    assert len(runtime.calls) == 1


@pytest.mark.asyncio
async def test_failed_auto_title_is_not_retried(service) -> None:
    chat_service, repository, runtime = service
    chat = repository.create_chat_with_message("New Chat", "user", "Hallo")
    repository.add_message(chat.id, "assistant", "Hallo Flo")

    call_count = 0

    async def failing_title_stream(messages):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            yield "Zweite Antwort"
            return
        raise RuntimeError("title generation failed")
        yield

    runtime.generate_text_stream = failing_title_stream

    turn = chat_service.start_turn(chat.id, "Zweite Frage")
    _ = [chunk async for chunk in chat_service.stream_response(turn)]
    await chat_service.finalize_turn(turn)

    loaded = repository.get_chat(chat.id)
    assert loaded is not None
    assert loaded.title == "New Chat"
    assert loaded.auto_title_attempted is True

    runtime.generate_text_stream = FakeRuntime().generate_text_stream
    third_turn = chat_service.start_turn(chat.id, "Dritte Frage")
    _ = [chunk async for chunk in chat_service.stream_response(third_turn)]
    await chat_service.finalize_turn(third_turn)

    loaded = repository.get_chat(chat.id)
    assert loaded is not None
    assert loaded.title == "New Chat"


def test_unknown_chat_is_rejected_before_streaming(service) -> None:
    chat_service, _, _ = service

    with pytest.raises(ChatNotFoundError):
        chat_service.start_turn(999, "Hallo")


def test_terminal_compression_error_rejects_before_persisting_user_message(
    service,
) -> None:
    chat_service, repository, _ = service
    chat = repository.create_chat("Chat")
    assert repository.set_compression_error_if_version(
        chat.id,
        expected_version=0,
        error_code="chat_context_compression_failed",
    )

    with pytest.raises(ChatCompressionFailedError, match="chat_context_compression_failed"):
        chat_service.start_turn(chat.id, "Weiter")

    assert repository.get_messages(chat.id) == []


@pytest.mark.asyncio
async def test_runtime_failure_keeps_user_without_partial_assistant(service) -> None:
    chat_service, repository, runtime = service

    async def failing_stream(messages):
        del messages
        yield "Teilantwort"
        raise RuntimeError("runtime failed")

    runtime.generate_text_stream = failing_stream

    turn = chat_service.start_turn(None, "Hallo")

    with pytest.raises(RuntimeError):
        _ = [chunk async for chunk in chat_service.stream_response(turn)]

    messages = repository.get_messages(turn.chat_id)
    assert [(message.role, message.content) for message in messages] == [
        ("user", "Hallo"),
    ]


@pytest.mark.asyncio
async def test_model_context_contains_all_uncompressed_messages(service) -> None:
    chat_service, repository, runtime = service
    chat = repository.create_chat_with_message("Chat", "user", "Message 0")

    for index in range(1, 100):
        repository.add_message(chat.id, "assistant", f"Message {index}")

    turn = chat_service.start_turn(chat.id, "Message 100")
    _ = [chunk async for chunk in chat_service.stream_response(turn)]

    assert runtime.messages is not None
    assert len(runtime.messages) == 103
    assert runtime.messages[0]["content"].startswith("Aktuelles Datum und Uhrzeit: ")
    assert runtime.messages[2]["content"] == "Message 0"
    assert runtime.messages[-1]["content"] == "Message 100"


if __name__ == "__main__":
    # Führt alle Tests in genau dieser Datei aus (__file__)
    pytest.main([__file__, "-v", "-s"])
