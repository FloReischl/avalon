from pathlib import Path

import pytest

from avalo_backend.runtime.llama_cpp import LlamaCppRuntime


@pytest.mark.skip(reason="Runtime implementation follows after the Gemma 4 spike.")
async def test_runtime_generates_german_text() -> None:
    runtime = LlamaCppRuntime()
    response = await runtime.generate_text("Antworte kurz auf Deutsch.")
    assert response


@pytest.mark.skip(reason="Native audio implementation follows after the Gemma 4 spike.")
async def test_runtime_accepts_native_audio() -> None:
    runtime = LlamaCppRuntime()
    response = await runtime.generate_from_audio(Path("sample.wav"))
    assert response

