import logging

import pytest

from app.config import LlmConfig
from app.main import validate_configured_llms


class FakeRuntime:
    def __init__(self, unavailable: set[str] | None = None) -> None:
        self._unavailable = unavailable or set()
        self.checked_models: list[str] = []

    async def model_exists(self, model: str) -> bool:
        self.checked_models.append(model)
        return model not in self._unavailable


MODELS = (
    LlmConfig(key="standard", model="test:standard", tool_support=True),
    LlmConfig(key="optional", model="test:optional", tool_support=False),
)


@pytest.mark.asyncio
async def test_startup_accepts_all_configured_llms() -> None:
    runtime = FakeRuntime()

    await validate_configured_llms(runtime, MODELS)  # type: ignore[arg-type]

    assert runtime.checked_models == [
        llm.model for llm in MODELS
    ]


@pytest.mark.asyncio
async def test_startup_rejects_missing_standard_llm(
    caplog: pytest.LogCaptureFixture,
) -> None:
    standard = MODELS[0]
    runtime = FakeRuntime({standard.model})

    with caplog.at_level(logging.ERROR):
        with pytest.raises(
            RuntimeError,
            match="Required LLM 'standard' is unavailable",
        ):
            await validate_configured_llms(runtime, MODELS)  # type: ignore[arg-type]

    assert standard.model in caplog.text
    assert runtime.checked_models == [standard.model]


@pytest.mark.asyncio
async def test_startup_warns_about_missing_optional_llm(
    caplog: pytest.LogCaptureFixture,
) -> None:
    standard = MODELS[0]
    optional = MODELS[1]
    runtime = FakeRuntime({optional.model})

    with caplog.at_level(logging.WARNING):
        await validate_configured_llms(runtime, MODELS)  # type: ignore[arg-type]

    assert optional.key in caplog.text
    assert optional.model in caplog.text
