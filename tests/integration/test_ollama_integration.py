import pytest
from app.runtime.ollama import OllamaRuntime
from pathlib import Path

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

    # Generate from audio
    response = await runtime.generate_from_audio(Path("tests/data/german-transcription.wav"))
    assert "diagnostizierte" in response, "The response from Ollama does not contain the expected transcript content."
