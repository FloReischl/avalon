import pytest

from app.runtime.llama_cpp import LlamaCppRuntime


@pytest.mark.anyio
async def test_llama_cpp_runtime_blueprint_is_not_implemented():
    runtime = LlamaCppRuntime()

    with pytest.raises(NotImplementedError):
        await runtime.generate_text("Hallo")
