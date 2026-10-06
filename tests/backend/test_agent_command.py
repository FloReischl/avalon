from types import SimpleNamespace

from app.commands.agent import AgentInviteCommand, AgentUnloadCommand


def test_agent_invite_help_uses_provided_agent_configuration_without_side_effects() -> None:
    agents = (
        SimpleNamespace(key="default", name="Default"),
        SimpleNamespace(key="hedwig", name="Hedwig"),
    )
    command = AgentInviteCommand(None, agents)  # type: ignore[arg-type]

    help_text = command.get_help()

    assert "/agent invite <agent> [-force]" in help_text
    assert "Invites an agent into the current chat." in help_text
    assert "-force    Replaces the currently active agent." in help_text
    assert "Default" in help_text
    assert "Hedwig" in help_text
    assert agents == (
        SimpleNamespace(key="default", name="Default"),
        SimpleNamespace(key="hedwig", name="Hedwig"),
    )


def test_agent_invite_help_handles_empty_agent_configuration() -> None:
    command = AgentInviteCommand(None, ())  # type: ignore[arg-type]

    assert "Available agents:\n  (none)" in command.get_help()


def test_agent_unload_help_describes_existing_command_contract() -> None:
    command = AgentUnloadCommand(None, ())  # type: ignore[arg-type]

    help_text = command.get_help()

    assert "/agent unload" in help_text
    assert "Unloads the current agent and switches back to the default agent." in help_text
    assert "No action if the default agent is already active." in help_text
