"""Deterministic context-compression primitives."""

import pytest

from app.services.context_compression import (
    CompressedContext,
    CompressionBudgetError,
    CompressionValidationError,
    estimate_tokens,
    garbage_collect_summaries,
    parse_compressed_context,
    serialize_messages,
)


def test_estimate_tokens_rounds_up_by_three_characters() -> None:
    assert estimate_tokens("x" * 32) == 11
    assert estimate_tokens("") == 0


def test_serialize_messages_preserves_roles_and_structure() -> None:
    messages = [{"role": "user", "content": "Hallo"}]

    assert serialize_messages(messages) == '[{"role":"user","content":"Hallo"}]'


def test_parse_accepts_only_the_complete_compressor_schema() -> None:
    parsed = parse_compressed_context(
        '{"summaries":["wichtig"],"stars":["Absicht"]}'
    )

    assert parsed == CompressedContext(("wichtig",), ("Absicht",))


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        '{"summaries":[],"stars":[],"extra":true}',
        '{"summaries":"no","stars":[]}',
        '{"summaries":[],"stars":["a","b","c"]}',
    ],
)
def test_parse_rejects_invalid_compressor_output(payload: str) -> None:
    with pytest.raises(CompressionValidationError):
        parse_compressed_context(payload)


def test_gc_discards_summaries_from_the_end_before_stars() -> None:
    context = CompressedContext(
        ("wichtig", "weniger wichtig", "entbehrlich"),
        ("langfristig",),
    )
    max_chars = len(
        CompressedContext(("wichtig",), ("langfristig",)).as_json()
    )

    compacted = garbage_collect_summaries(context, max_chars)

    assert compacted == CompressedContext(("wichtig",), ("langfristig",))


def test_gc_never_discards_stars() -> None:
    context = CompressedContext((), ("zu lang",))

    with pytest.raises(CompressionBudgetError):
        garbage_collect_summaries(context, 1)
