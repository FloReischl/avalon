from pathlib import Path

import pytest

from app.models_config import ModelsConfig
from app.state import AvalonState
from app.user_config import load_user_config


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLUEPRINT_CONFIG = (
    PROJECT_ROOT
    / "data"
    / "blueprints"
    / "user.avalon"
    / "config.yaml"
)


def config_with_second_avatar():
    config = load_user_config(BLUEPRINT_CONFIG)
    second_avatar = config.standard_avatar.model_copy(
        update={"key": "second"},
        deep=True,
    )
    return config.model_copy(
        update={
            "avatars": [
                config.standard_avatar,
                second_avatar,
            ]
        },
        deep=True,
    )


def models_config() -> ModelsConfig:
    return ModelsConfig.model_validate(
        {"models": [
            {"key": "standard", "model": "test:standard", "tool_support": True},
            {"key": "uncensored", "model": "test:optional", "tool_support": False},
        ]}
    )


def test_avalon_state_starts_with_standard_avatar() -> None:
    config = load_user_config(BLUEPRINT_CONFIG)

    state = AvalonState(config, models_config())

    assert state.user_config is config
    assert state.current_avatar is config.standard_avatar


def test_avalon_state_starts_with_standard_llm() -> None:
    config = load_user_config(BLUEPRINT_CONFIG)
    catalog = models_config()
    state = AvalonState(config, catalog)

    standard = next(llm for llm in catalog.llm_models if llm.key == "standard")

    assert state.current_llm == standard
    assert state.llm_inference_active is False


def test_avalon_state_switches_current_llm() -> None:
    config = load_user_config(BLUEPRINT_CONFIG)
    state = AvalonState(config, models_config())

    changed = state.set_current_llm("uncensored")

    assert changed is True
    assert state.current_llm.key == "uncensored"


def test_avalon_state_rejects_unknown_llm_without_state_change() -> None:
    config = load_user_config(BLUEPRINT_CONFIG)
    state = AvalonState(config, models_config())
    selected = state.current_llm

    changed = state.set_current_llm("missing")

    assert changed is False
    assert state.current_llm is selected


def test_llm_lookup_is_case_sensitive() -> None:
    config = load_user_config(BLUEPRINT_CONFIG)
    state = AvalonState(config, models_config())

    changed = state.set_current_llm("UNCENSORED")

    assert changed is False
    assert state.current_llm.key == "standard"


def test_avalon_state_guards_llm_switch_state() -> None:
    config = load_user_config(BLUEPRINT_CONFIG)
    state = AvalonState(config, models_config())

    state.begin_llm_switch()

    assert state.llm_switch_active is True

    state.end_llm_switch()

    assert state.llm_switch_active is False


def test_avalon_state_rejects_llm_switch_during_inference() -> None:
    config = load_user_config(BLUEPRINT_CONFIG)
    state = AvalonState(config, models_config())

    state.begin_llm_inference()

    with pytest.raises(RuntimeError, match="LLM inference is active"):
        state.begin_llm_switch()

    state.end_llm_inference()


def test_avalon_state_tracks_concurrent_llm_inferences() -> None:
    config = load_user_config(BLUEPRINT_CONFIG)
    state = AvalonState(config, models_config())

    state.begin_llm_inference()
    state.begin_llm_inference()

    assert state.llm_inference_active is True

    state.end_llm_inference()
    assert state.llm_inference_active is True

    state.end_llm_inference()
    assert state.llm_inference_active is False


def test_avalon_state_rejects_llm_inference_counter_underflow() -> None:
    config = load_user_config(BLUEPRINT_CONFIG)
    state = AvalonState(config, models_config())

    with pytest.raises(RuntimeError, match="LLM inference counter underflow"):
        state.end_llm_inference()


def test_avalon_state_switches_current_avatar() -> None:
    config = config_with_second_avatar()
    state = AvalonState(config, models_config())

    changed = state.set_current_avatar("second")

    assert changed is True
    assert state.current_avatar.key == "second"


def test_avalon_state_rejects_unknown_avatar_without_state_change() -> None:
    config = config_with_second_avatar()
    state = AvalonState(config, models_config())

    assert state.set_current_avatar("second") is True
    selected = state.current_avatar

    changed = state.set_current_avatar("missing")

    assert changed is False
    assert state.current_avatar is selected


def test_avatar_lookup_is_case_sensitive() -> None:
    config = config_with_second_avatar()
    state = AvalonState(config, models_config())

    changed = state.set_current_avatar("SECOND")

    assert changed is False
    assert state.current_avatar.key == "standard"
