from types import SimpleNamespace

import pytest

from app.commands.avatar_set import AvatarCommand
from app.commands.factory import build_command_registry
from app.commands.parser import CommandRequest, parse_command


class FakeState:
    def __init__(self) -> None:
        self.current_avatar = SimpleNamespace(key="standard")
        self._avatars = {
            "standard": self.current_avatar,
            "second": SimpleNamespace(key="second"),
        }

    @property
    def avatars(self):
        return tuple(self._avatars.values())

    def set_current_avatar(self, key: str) -> bool:
        avatar = self._avatars.get(key)
        if avatar is None:
            return False

        self.current_avatar = avatar
        return True


@pytest.mark.asyncio
async def test_avatar_command_switches_current_avatar() -> None:
    state = FakeState()
    command = AvatarCommand(state)  # type: ignore[arg-type]

    response = await command.execute("second")

    assert response == "ok"
    assert state.current_avatar.key == "second"


@pytest.mark.asyncio
async def test_avatar_command_rejects_invalid_avatar_without_state_change() -> None:
    state = FakeState()
    command = AvatarCommand(state)  # type: ignore[arg-type]
    selected = state.current_avatar

    response = await command.execute("missing")

    assert response == "invalid avatar key"
    assert state.current_avatar is selected


@pytest.mark.asyncio
async def test_avatar_command_payload_is_case_sensitive() -> None:
    state = FakeState()
    command = AvatarCommand(state)  # type: ignore[arg-type]

    response = await command.execute("SECOND")

    assert response == "invalid avatar key"
    assert state.current_avatar.key == "standard"


def test_avatar_command_help_uses_current_state_avatars_without_side_effects() -> None:
    state = FakeState()
    command = AvatarCommand(state)  # type: ignore[arg-type]
    selected = state.current_avatar

    help_text = command.get_help()

    assert "/avatar set <avatar>" in help_text
    assert "Changes the avatar theme." in help_text
    assert "standard" in help_text
    assert "second" in help_text
    assert state.current_avatar is selected


def test_avatar_command_help_handles_empty_avatar_catalog() -> None:
    state = FakeState()
    state._avatars = {}
    command = AvatarCommand(state)  # type: ignore[arg-type]

    assert "Available avatars:\n  (none)" in command.get_help()


@pytest.mark.asyncio
async def test_command_registry_factory_registers_avatar_command() -> None:
    state = FakeState()
    registry = build_command_registry(state)  # type: ignore[arg-type]
    request = parse_command("/avatar set second")

    assert request is not None
    matched = registry.match(request)
    assert matched == CommandRequest(key="avatar set", payload="second")

    response = await registry.execute(
        matched
    )

    assert response == "ok"
    assert state.current_avatar.key == "second"
