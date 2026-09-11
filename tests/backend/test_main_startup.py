import logging

import pytest

from app.config import settings
from app.main import validate_configured_llms


class FakeRuntime:
    def __init__(self, unavailable: set[str] | None = None) -> None:
        self._unavailable = unavailable or set()
        self.checked_models: list[str] = []

    async def model_exists(self, model: str) -> bool:
        self.checked_models.append(model)
        return model not in self._unavailable


@pytest.mark.asyncio
async def test_startup_accepts_all_configured_llms() -> None:
    runtime = FakeRuntime()

    await validate_configured_llms(runtime)  # type: ignore[arg-type]

    assert runtime.checked_models == [
        llm.model for llm in settings.llm_models
    ]


@pytest.mark.asyncio
async def test_startup_rejects_missing_standard_llm(
    caplog: pytest.LogCaptureFixture,
) -> None:
    standard = next(
        llm for llm in settings.llm_models if llm.key == "standard"
    )
    runtime = FakeRuntime({standard.model})

    with caplog.at_level(logging.ERROR):
        with pytest.raises(
            RuntimeError,
            match="Required LLM 'standard' is unavailable",
        ):
            await validate_configured_llms(runtime)  # type: ignore[arg-type]

    assert standard.model in caplog.text
    assert runtime.checked_models == [standard.model]


@pytest.mark.asyncio
async def test_startup_warns_about_missing_optional_llm(
    caplog: pytest.LogCaptureFixture,
) -> None:
    optional = next(
        llm for llm in settings.llm_models if llm.key != "standard"
    )
    runtime = FakeRuntime({optional.model})

    with caplog.at_level(logging.WARNING):
        await validate_configured_llms(runtime)  # type: ignore[arg-type]

    assert optional.key in caplog.text
    assert optional.model in caplog.text