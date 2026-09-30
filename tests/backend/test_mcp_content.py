"""Tests for content.create-audio MCP tool and permission."""

from __future__ import annotations

import asyncio
import json
import pytest

from app.authorization.permissions import ContentCreateAudioPermission
from app.authorization.exceptions import PermissionDenied
from app.mcp.server import create_mcp_server
from app.mcp.security import current_principal_id
import app.mcp.server as mcp_server_module
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


@pytest.mark.asyncio
async def test_mcp_call_denies_audio_creation_outside_scope(monkeypatch) -> None:
    class FakeEngine:
        def dispose(self):
            pass

    class FakeRepository:
        def __init__(self, _):
            pass

        def get_principal_permission_catalog_ids(self, principal_id):
            return {42}

        def get_permission_catalog_id(self, context, key):
            assert (context, key) == ("content", "create-audio")
            return 42

        def get_principal_permission_by_catalog_id(self, principal_id, catalog_id):
            return PrincipalPermission(
                principal_id=principal_id,
                permission_catalog_id=catalog_id,
                scope=json.dumps(["/tmp/allowed"]),
                validity_type="duration",
                default_expiry=7200,
            )

        def get_grants(self, definition_id):
            return []

    monkeypatch.setattr(mcp_server_module, "AuthorizationRepository", FakeRepository)
    monkeypatch.setattr(mcp_server_module, "create_database_engine", FakeEngine)
    monkeypatch.setattr(mcp_server_module, "create_session_factory", lambda _: object())

    token = current_principal_id.set(7)
    try:
        service = FakeAudioCreationService()
        mcp = create_mcp_server(audio_creation_service=service)
        with pytest.raises(PermissionDenied, match="content/create-audio is not allowed by principal scope"):
            await mcp.call_tool(
                "content.create-audio",
                {"content": "Hello", "output_file": "/tmp/forbidden/audio.mp3"},
            )
        assert service.calls == []
    finally:
        current_principal_id.reset(token)
