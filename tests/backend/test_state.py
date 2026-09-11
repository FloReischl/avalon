from pathlib import Path

from app.state import AvaloState
from app.user_config import load_user_config


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLUEPRINT_CONFIG = (
    PROJECT_ROOT
    / "data"
    / "blueprints"
    / "user.avalo"
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


def test_avalo_state_starts_with_standard_avatar() -> None:
    config = load_user_config(BLUEPRINT_CONFIG)

    state = AvaloState(config)

    assert state.user_config is config
    assert state.current_avatar is config.standard_avatar


def test_avalo_state_switches_current_avatar() -> None:
    config = config_with_second_avatar()
    state = AvaloState(config)

    changed = state.set_current_avatar("second")

    assert changed is True
    assert state.current_avatar.key == "second"


def test_avalo_state_rejects_unknown_avatar_without_state_change() -> None:
    config = config_with_second_avatar()
    state = AvaloState(config)

    assert state.set_current_avatar("second") is True
    selected = state.current_avatar

    changed = state.set_current_avatar("missing")

    assert changed is False
    assert state.current_avatar is selected


def test_avatar_lookup_is_case_sensitive() -> None:
    config = config_with_second_avatar()
    state = AvaloState(config)

    changed = state.set_current_avatar("SECOND")

    assert changed is False
    assert state.current_avatar.key == "standard"