"""Tests for content.create-audio MCP tool and permission."""

from __future__ import annotations

import asyncio
import json
import pytest

from app.authorization.permissions import ContentCreateAudioPermission
from app.mcp.server import create_mcp_server
from app.persistence.models import PrincipalPermission


class FakeAudioCreationService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def create_audio(self, content: str, output_file: str) -> None:
        self.calls.append((content, output_file))


def test_content_create_audio_permission_allows_paths_in_scope() -> None:
    permission = ContentCreateAudioPermission()
    pp = PrincipalPermission(
        scope=json.dumps(["/tmp/avalon/audio"]),
        validity_type="duration",
        default_expiry=7200,
    )

    assert permission.allows(pp, ["/tmp/avalon/audio/lorem.mp3"])
    assert permission.allows(pp, ["/tmp/avalon/audio/sub/test.mp3"])
    assert not permission.allows(pp, ["/etc/passwd"])
    assert not permission.allows(pp, ["/tmp/other/audio.mp3"])


def test_content_create_audio_permission_items_and_formatting() -> None:
    permission = ContentCreateAudioPermission()
    args = {"content": "Lorem ipsum", "output_file": "/tmp/avalon/audio/lorem.mp3"}

    items = permission.items(args)
    assert items == ["/tmp/avalon/audio/lorem.mp3"]
    assert permission.format(items[0]) == "Audiodatei erzeugen: /tmp/avalon/audio/lorem.mp3"

    approved = permission.approved_arguments(items, args)
    assert approved == args


def test_mcp_server_exposes_content_tool() -> None:
    mcp = create_mcp_server(audio_creation_service=FakeAudioCreationService())  # type: ignore[arg-type]
    tools = asyncio.run(mcp.list_tools())
    tool_names = [tool.name for tool in tools]
    assert "content.create-audio" in tool_names


@pytest.mark.asyncio
async def test_content_tool_delegates_to_service() -> None:
    service = FakeAudioCreationService()
    mcp = create_mcp_server(audio_creation_service=service)  # type: ignore[arg-type]

    await mcp.call_tool("content.create-audio", {"content": "Test content", "output_file": "/tmp/avalon/audio/test.mp3"})
    assert service.calls == [("Test content", "/tmp/avalon/audio/test.mp3")]
