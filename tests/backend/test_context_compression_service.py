"""Compression orchestration with deterministic fake model output."""

from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.config import settings
from app.persistence.chat_repository import ChatRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.persistence.migrations import run_migrations
from app.services.context_compression import (
    COMPRESSED_CONTEXT_PREFIX,
    ContextCompressionService,
    _available_compression_chars,
    build_active_context,
    parse_compressed_context,
)


DEFAULT_AGENT = SimpleNamespace(
    key="default",
    persona="Du bist Frieda.",
    instructions="Antworte kurz.",
)


class FakeRuntime:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.prompts: list[list[dict[str, str]]] = []

    async def generate_text_stream(
        self,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        self.prompts.append(messages)
        output = self.outputs.pop(0)
        if output == "RUNTIME_ERROR":
            raise RuntimeError("offline")
        yield output


@pytest.fixture
def repository(tmp_path: Path):
    path = tmp_path / "avalon.sqlite"
    run_migrations(path)
    engine = create_database_engine(path)
    try:
        yield ChatRepository(create_session_factory(engine))
    finally:
        engine.dispose()


@pytest.fixture
def compression_settings(monkeypatch):
    import app.services.context_compression as compression_module

    configured = replace(
        settings,
        context_compression_trigger_tokens=1,
        context_compression_target_tokens=1_000,
        context_compression_max_attempts=3,
    )
    monkeypatch.setattr(compression_module, "settings", configured)
    return configured


def add_roundtrips(repository: ChatRepository, count: int) -> int:
    chat = repository.create_chat("Chat", agent_id=1)
    for index in range(count):
        repository.add_message(chat.id, "user", f"Frage {index}")
        repository.add_message(chat.id, "assistant", f"Antwort {index}")
    return chat.id


def compression_service(runtime: FakeRuntime, repository: ChatRepository) -> ContextCompressionService:
    return ContextCompressionService(runtime, repository, agents=(DEFAULT_AGENT,))


@pytest.mark.asyncio
async def test_compression_represents_only_unprotected_old_roundtrips(
    repository: ChatRepository,
    compression_settings,
) -> None:
    chat_id = add_roundtrips(repository, 3)
    runtime = FakeRuntime(['{"summaries":["frueher"],"stars":["Ziel"]}'])

    await compression_service(runtime, repository).compress_if_needed(chat_id)

    chat = repository.get_chat(chat_id)
    assert chat is not None
    assert chat.compression_version == 1
    assert chat.compressed_through_seq == 2
    assert parse_compressed_context(chat.compressed_context).summaries == ("frueher",)
    submitted = runtime.prompts[0][1]["content"]
    assert '"seq":1' in submitted
    assert '"seq":2' in submitted
    assert '"seq":3' not in submitted
    protected = repository.get_messages(chat_id)[2:]
    expected_max_chars = _available_compression_chars(protected, DEFAULT_AGENT)
    assert (
        f"max_chars-Budgets bleiben: {expected_max_chars} Zeichen"
        in runtime.prompts[0][0]["content"]
    )


@pytest.mark.asyncio
async def test_compressor_receives_recalculated_budget_after_protected_retry(
    repository: ChatRepository,
    monkeypatch,
) -> None:
    import app.services.context_compression as compression_module

    monkeypatch.setattr(
        compression_module,
        "settings",
        replace(
            settings,
            context_compression_trigger_tokens=1,
            context_compression_target_tokens=150,
            context_compression_max_attempts=3,
        ),
    )
    chat_id = add_roundtrips(repository, 3)
    output = '{"summaries":[],"stars":["' + ("x" * 300) + '"]}'
    runtime = FakeRuntime([output, output, output])

    await compression_service(runtime, repository).compress_if_needed(chat_id)

    messages = repository.get_messages(chat_id)
    normal_max_chars = _available_compression_chars(messages[2:], DEFAULT_AGENT)
    fallback_max_chars = _available_compression_chars([], DEFAULT_AGENT)
    assert normal_max_chars < fallback_max_chars
    assert len(runtime.prompts) == 3
    assert (
        f"max_chars-Budgets bleiben: {normal_max_chars} Zeichen"
        in runtime.prompts[0][0]["content"]
    )
    assert (
        f"max_chars-Budgets bleiben: {fallback_max_chars} Zeichen"
        in runtime.prompts[1][0]["content"]
    )


@pytest.mark.asyncio
async def test_context_at_or_below_trigger_does_not_call_compressor(
    repository: ChatRepository,
    monkeypatch,
) -> None:
    import app.services.context_compression as compression_module

    monkeypatch.setattr(
        compression_module,
        "settings",
        replace(settings, context_compression_trigger_tokens=10_000),
    )
    chat_id = add_roundtrips(repository, 1)
    runtime = FakeRuntime([])

    await compression_service(runtime, repository).compress_if_needed(chat_id)

    assert runtime.prompts == []


@pytest.mark.asyncio
async def test_invalid_results_are_retried_but_do_not_set_terminal_error(
    repository: ChatRepository,
    compression_settings,
) -> None:
    chat_id = add_roundtrips(repository, 3)
    runtime = FakeRuntime(["not json", "not json", "not json"])

    await compression_service(runtime, repository).compress_if_needed(chat_id)

    chat = repository.get_chat(chat_id)
    assert chat is not None
    assert len(runtime.prompts) == 3
    assert chat.compression_version == 0
    assert chat.compression_error_code is None


@pytest.mark.asyncio
async def test_runtime_failure_does_not_change_compression_state(
    repository: ChatRepository,
    compression_settings,
) -> None:
    chat_id = add_roundtrips(repository, 3)
    runtime = FakeRuntime(["RUNTIME_ERROR"])

    await compression_service(runtime, repository).compress_if_needed(chat_id)

    chat = repository.get_chat(chat_id)
    assert chat is not None
    assert chat.compression_version == 0
    assert chat.compression_error_code is None


@pytest.mark.asyncio
async def test_unfulfillable_star_budget_sets_terminal_error(
    repository: ChatRepository,
    monkeypatch,
) -> None:
    import app.services.context_compression as compression_module

    monkeypatch.setattr(
        compression_module,
        "settings",
        replace(
            settings,
            context_compression_trigger_tokens=1,
            context_compression_target_tokens=1,
            context_compression_max_attempts=3,
        ),
    )
    chat_id = add_roundtrips(repository, 3)
    runtime = FakeRuntime(
        ['{"summaries":[],"stars":["unverzichtbar"]}'] * 3
    )

    await compression_service(runtime, repository).compress_if_needed(chat_id)

    chat = repository.get_chat(chat_id)
    assert chat is not None
    assert chat.compression_error_code == "chat_context_compression_failed"
    assert chat.compression_version == 0


def test_active_context_keeps_compressed_context_and_newer_original_messages(
    repository: ChatRepository,
) -> None:
    chat_id = add_roundtrips(repository, 2)
    messages = repository.get_messages(chat_id)
    compressed = parse_compressed_context(
        '{"summaries":["alte Information"],"stars":[]}'
    )

    context = build_active_context(
        messages, compressed, 2, None, now=datetime(2026, 9, 23, 14, 35)
    )

    assert context[0] == {
        "role": "system",
        "content": "Aktuelles Datum und Uhrzeit: 2026-09-23 14:35 (Europe/Berlin)\nAktueller Ort: München, Deutschland",
    }
    assert context[1]["role"] == "system"
    assert context[1]["content"].startswith(COMPRESSED_CONTEXT_PREFIX)
    assert [(message["role"], message["content"]) for message in context[2:]] == [
        ("user", "Frage 1"),
        ("assistant", "Antwort 1"),
    ]
