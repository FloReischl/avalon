import pytest

from app.commands.llm import LlmCommand
from app.config import settings


class FakeState:
    def __init__(self) -> None:
        self.current_llm = next(
            llm for llm in settings.llm_models if llm.key == "standard"
        )
        self.llm_inference_active = False
        self.llm_switch_active = False

    def begin_llm_switch(self) -> None:
        if self.llm_switch_active:
            raise RuntimeError("LLM switch is already active.")
        if self.llm_inference_active:
            raise RuntimeError("LLM inference is active.")
        self.llm_switch_active = True

    def end_llm_switch(self) -> None:
        self.llm_switch_active = False

    def set_current_llm(self, key: str) -> bool:
        llm = next(
            (
                llm
                for llm in settings.llm_models
                if llm.key == key
            ),
            None,
        )
        if llm is None:
            return False

        self.current_llm = llm
        return True


class FakeRuntime:
    def __init__(self) -> None:
        self.missing_models: set[str] = set()
        self.failed_warmups: set[str] = set()
        self.exists_calls: list[str] = []
        self.unload_calls: list[str] = []
        self.warm_up_calls: list[str] = []

    async def model_exists(self, model: str) -> bool:
        self.exists_calls.append(model)
        return model not in self.missing_models

    async def unload_model(self, model: str) -> None:
        self.unload_calls.append(model)

    async def warm_up_model(self, model: str) -> None:
        self.warm_up_calls.append(model)
        if model in self.failed_warmups:
            raise RuntimeError(f"warm-up failed: {model}")


def optional_llm():
    return next(
        llm for llm in settings.llm_models if llm.key != "standard"
    )


@pytest.mark.asyncio
async def test_llm_command_rejects_unknown_key() -> None:
    state = FakeState()
    runtime = FakeRuntime()
    command = LlmCommand(state, runtime)  # type: ignore[arg-type]

    response = await command.execute("missing")

    assert response == "Unknown LLM: 'missing'."
    assert state.current_llm.key == "standard"
    assert runtime.exists_calls == []
    assert runtime.unload_calls == []
    assert runtime.warm_up_calls == []


@pytest.mark.asyncio
async def test_llm_command_rejects_switch_during_inference() -> None:
    state = FakeState()
    runtime = FakeRuntime()
    state.llm_inference_active = True
    command = LlmCommand(state, runtime)  # type: ignore[arg-type]

    response = await command.execute(optional_llm().key)

    assert response == "LLM inference is active."
    assert state.current_llm.key == "standard"
    assert runtime.exists_calls == []
    assert runtime.unload_calls == []
    assert runtime.warm_up_calls == []


@pytest.mark.asyncio
async def test_llm_command_same_key_is_successful_noop() -> None:
    state = FakeState()
    runtime = FakeRuntime()
    command = LlmCommand(state, runtime)  # type: ignore[arg-type]

    response = await command.execute("standard")

    assert response == "'standard' already active."
    assert runtime.exists_calls == []
    assert runtime.unload_calls == []
    assert runtime.warm_up_calls == []


@pytest.mark.asyncio
async def test_llm_command_rejects_unavailable_configured_model() -> None:
    state = FakeState()
    runtime = FakeRuntime()
    target = optional_llm()
    runtime.missing_models.add(target.model)
    command = LlmCommand(state, runtime)  # type: ignore[arg-type]

    response = await command.execute(target.key)

    assert response == f"LLM '{target.key}' is unavailable."
    assert state.current_llm.key == "standard"
    assert runtime.exists_calls == [target.model]
    assert runtime.unload_calls == []
    assert runtime.warm_up_calls == []
    assert state.llm_switch_active is False


@pytest.mark.asyncio
async def test_llm_command_switches_model() -> None:
    state = FakeState()
    runtime = FakeRuntime()
    target = optional_llm()
    previous = state.current_llm
    command = LlmCommand(state, runtime)  # type: ignore[arg-type]

    response = await command.execute(target.key)

    assert response == f"'{target.key}' activated."
    assert state.current_llm is target
    assert runtime.exists_calls == [target.model]
    assert runtime.unload_calls == [previous.model]
    assert runtime.warm_up_calls == [target.model]
    assert state.llm_switch_active is False


@pytest.mark.asyncio
async def test_llm_command_recovers_previous_model_after_target_warmup_failure() -> None:
    state = FakeState()
    runtime = FakeRuntime()
    target = optional_llm()
    previous = state.current_llm
    runtime.failed_warmups.add(target.model)
    command = LlmCommand(state, runtime)  # type: ignore[arg-type]

    with pytest.raises(
        RuntimeError,
        match=f"Failed to activate LLM '{target.key}'",
    ):
        await command.execute(target.key)

    assert state.current_llm is previous
    assert runtime.unload_calls == [previous.model]
    assert runtime.warm_up_calls == [
        target.model,
        previous.model,
    ]
    assert state.llm_switch_active is False


@pytest.mark.asyncio
async def test_llm_command_exits_when_previous_model_cannot_be_recovered() -> None:
    state = FakeState()
    runtime = FakeRuntime()
    target = optional_llm()
    previous = state.current_llm
    runtime.failed_warmups.update(
        {
            target.model,
            previous.model,
        }
    )
    command = LlmCommand(state, runtime)  # type: ignore[arg-type]

    with pytest.raises(
        SystemExit,
        match=f"Failed to recover previous LLM '{previous.key}'",
    ):
        await command.execute(target.key)

    assert state.current_llm is previous
    assert runtime.warm_up_calls == [
        target.model,
        previous.model,
    ]
    assert state.llm_switch_active is False