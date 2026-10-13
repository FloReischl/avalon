from pathlib import Path

import pytest

from app.models_config import ModelsConfig
from app.state import AvalonState
from app.avatars_config import load_avatars_config
from app.user_config import load_user_config


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLUEPRINT_CONFIG = (
    PROJECT_ROOT
    / "data"
    / "blueprints"
    / "user.avalon"
    / "config.yaml"
)
BLUEPRINT_AVATARS_CONFIG = BLUEPRINT_CONFIG.with_name("avatars.yaml")


def config_with_second_avatar():
    avatars_config = load_avatars_config(BLUEPRINT_AVATARS_CONFIG)
    second_avatar = avatars_config.standard_avatar.model_copy(
        update={"key": "second"},
        deep=True,
    )
    return avatars_config.model_copy(
        update={
            "avatars": [
                avatars_config.standard_avatar,
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


def make_state(avatars_config=None) -> AvalonState:
    return AvalonState(
        load_user_config(BLUEPRINT_CONFIG),
        avatars_config or load_avatars_config(BLUEPRINT_AVATARS_CONFIG),
        models_config(),
    )


def test_avalon_state_starts_with_standard_avatar() -> None:
    config = load_user_config(BLUEPRINT_CONFIG)
    avatars_config = load_avatars_config(BLUEPRINT_AVATARS_CONFIG)

    state = AvalonState(config, avatars_config, models_config())

    assert state.user_config is config
    assert state.current_avatar is avatars_config.standard_avatar
    assert state.user_config.mail is not None
    assert state.user_config.mail.google.account == "florian.reischl@gmail.com"


def test_avalon_state_starts_with_standard_llm() -> None:
    catalog = models_config()
    state = AvalonState(load_user_config(BLUEPRINT_CONFIG), load_avatars_config(BLUEPRINT_AVATARS_CONFIG), catalog)

    standard = next(llm for llm in catalog.llm_models if llm.key == "standard")

    assert state.current_llm == standard
    assert state.llm_inference_active is False


def test_avalon_state_switches_current_llm() -> None:
    state = make_state()

    changed = state.set_current_llm("uncensored")

    assert changed is True
    assert state.current_llm.key == "uncensored"


def test_avalon_state_rejects_unknown_llm_without_state_change() -> None:
    state = make_state()
    selected = state.current_llm

    changed = state.set_current_llm("missing")

    assert changed is False
    assert state.current_llm is selected


def test_llm_lookup_is_case_sensitive() -> None:
    state = make_state()

    changed = state.set_current_llm("UNCENSORED")

    assert changed is False
    assert state.current_llm.key == "standard"


def test_avalon_state_guards_llm_switch_state() -> None:
    state = make_state()

    state.begin_llm_switch()

    assert state.llm_switch_active is True

    state.end_llm_switch()

    assert state.llm_switch_active is False


def test_avalon_state_rejects_llm_switch_during_inference() -> None:
    state = make_state()

    state.begin_llm_inference()

    with pytest.raises(RuntimeError, match="LLM inference is active"):
        state.begin_llm_switch()

    state.end_llm_inference()


def test_avalon_state_tracks_concurrent_llm_inferences() -> None:
    state = make_state()

    state.begin_llm_inference()
    state.begin_llm_inference()

    assert state.llm_inference_active is True

    state.end_llm_inference()
    assert state.llm_inference_active is True

    state.end_llm_inference()
    assert state.llm_inference_active is False


def test_avalon_state_rejects_llm_inference_counter_underflow() -> None:
    state = make_state()

    with pytest.raises(RuntimeError, match="LLM inference counter underflow"):
        state.end_llm_inference()


def test_avalon_state_switches_current_avatar() -> None:
    state = make_state(config_with_second_avatar())

    changed = state.set_current_avatar("second")

    assert changed is True
    assert state.current_avatar.key == "second"


def test_avalon_state_rejects_unknown_avatar_without_state_change() -> None:
    state = make_state(config_with_second_avatar())

    assert state.set_current_avatar("second") is True
    selected = state.current_avatar

    changed = state.set_current_avatar("missing")

    assert changed is False
    assert state.current_avatar is selected


def test_avatar_lookup_is_case_sensitive() -> None:
    state = make_state(config_with_second_avatar())

    changed = state.set_current_avatar("SECOND")

    assert changed is False
    assert state.current_avatar.key == "standard"
