from types import SimpleNamespace

import pytest

from app.commands.avatar import AvatarCommand
from app.commands.factory import build_command_registry
from app.commands.parser import CommandRequest


class FakeState:
    def __init__(self) -> None:
        self.current_avatar = SimpleNamespace(key="standard")
        self._avatars = {
            "standard": self.current_avatar,
            "second": SimpleNamespace(key="second"),
        }

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


@pytest.mark.asyncio
async def test_command_registry_factory_registers_avatar_command() -> None:
    state = FakeState()
    registry = build_command_registry(state)  # type: ignore[arg-type]

    response = await registry.execute(
        CommandRequest(
            key="avatar",
            payload="second",
        )
    )

    assert response == "ok"
    assert state.current_avatar.key == "second"