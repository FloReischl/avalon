import pytest
from app.runtime.ollama import OllamaRuntime


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ollama_runtime_integration():
    runtime = OllamaRuntime()

    # Check health
    assert await runtime.health(), "Ollama is not reachable or the model is not available."

    # Generate text
    prompt = "Was ist die Hauptstadt von Deutschland?"
    response = await runtime.generate_text(prompt)
    assert response.strip(), "The response from Ollama is empty or only contains whitespace."
