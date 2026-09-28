from types import SimpleNamespace
from pathlib import Path

import pytest

from app.models_config import load_models_config
from app.runtime.ollama import OllamaRuntime

@pytest.mark.integration
@pytest.mark.asyncio
async def test_ollama_runtime_integration():
    standard = next(
        llm
        for llm in load_models_config(
            Path(__file__).resolve().parents[2] / "data/blueprints/user.avalon/models.yaml"
        ).llm_models
        if llm.key == "standard"
    )
    state = SimpleNamespace(
        current_llm=standard,
        llm_switch_active=False,
        begin_llm_inference=lambda: None,
        end_llm_inference=lambda: None,
    )
    runtime = OllamaRuntime(lambda: state)

    # Check health
    assert await runtime.health(), "Ollama is not reachable or the model is not available."

    # Generate text
    prompt = "Was ist die Hauptstadt von Deutschland?"
    response = await runtime.generate_text(prompt)
    assert response.strip(), "The response from Ollama is empty or only contains whitespace."

    # Generate streaming text
    streamed_response = "".join(
        [
            chunk
            async for chunk in runtime.generate_text_stream(
                [{"role": "user", "content": prompt}],
            )
        ],
    )
    assert streamed_response.strip(), "The streamed response from Ollama is empty or only contains whitespace."
