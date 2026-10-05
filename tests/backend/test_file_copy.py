"""Focused security and behavior tests for ``file.copy``."""

from __future__ import annotations

import json
import os
import stat
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.authorization.permissions import FileCopyPermission
from app.mcp.security import current_principal_id
from app.mcp.server import create_mcp_server
import app.mcp.server as mcp_server_module
from app.persistence.models import PrincipalPermission
from app.services.file_copy import FileCopyScope, FileCopyService


def _scope(source: Path, destination: Path) -> PrincipalPermission:
    return PrincipalPermission(
        scope=json.dumps([{"source": str(source), "destination": str(destination)}]),
        validity_type="duration",
        default_expiry=7200,
    )


def _copy(source: Path, destination: Path, source_root: Path, destination_root: Path) -> None:
    FileCopyService().copy(
        str(source), str(destination), FileCopyScope(source_root, destination_root)
    )


def test_permission_requires_one_paired_scope_and_rejects_dotdot(tmp_path: Path) -> None:
    source_root, destination_root = tmp_path / "source", tmp_path / "destination"
    source_root.mkdir()
    destination_root.mkdir()
    permission = FileCopyPermission()
    definition = _scope(source_root, destination_root)

    assert permission.allows(definition, permission.items({"source": str(source_root / "a"), "destination": str(destination_root / "b")}))
    assert not permission.allows(definition, permission.items({"source": str(tmp_path / "outside"), "destination": str(destination_root / "b")}))
    assert not permission.allows(definition, permission.items({"source": str(source_root / "a"), "destination": str(tmp_path / "outside")}))
    with pytest.raises(ValueError, match=r"without '\.\.'"):
        permission.items({"source": str(source_root / ".." / "other"), "destination": str(destination_root / "b")})


def test_file_copy_directory_destination_rename_overwrite_and_copy2(tmp_path: Path) -> None:
    source_root, destination_root = tmp_path / "source", tmp_path / "destination"
    source_root.mkdir()
    destination_root.mkdir()
    source = source_root / "track.mp3"
    source.write_text("new")
    stamp = 1_700_000_000
    os.utime(source, (stamp, stamp))
    existing_directory = destination_root / "podcasts"
    existing_directory.mkdir()
    (existing_directory / "track.mp3").write_text("old")

    _copy(source, existing_directory, source_root, destination_root)
    assert (existing_directory / "track.mp3").read_text() == "new"
    assert (existing_directory / "track.mp3").stat().st_mtime == stamp

    _copy(source, destination_root / "nested" / "renamed.mp3", source_root, destination_root)
    assert (destination_root / "nested" / "renamed.mp3").read_text() == "new"


def test_directory_copy_merges_contents_and_keeps_unrelated_files(tmp_path: Path) -> None:
    source_root, destination_root = tmp_path / "source", tmp_path / "destination"
    (source_root / "dir1").mkdir(parents=True)
    destination_root.mkdir()
    (source_root / "dir1" / "file1").write_text("new")
    (source_root / "dir1" / "file2").write_text("added")
    (destination_root / "dir1").mkdir()
    (destination_root / "dir1" / "file1").write_text("old")
    (destination_root / "dir1" / "file3").write_text("keep")

    _copy(source_root, destination_root, source_root, destination_root)
    assert (destination_root / "dir1" / "file1").read_text() == "new"
    assert (destination_root / "dir1" / "file2").read_text() == "added"
    assert (destination_root / "dir1" / "file3").read_text() == "keep"


def test_preflight_rejects_source_destination_and_symlink_escapes_without_writes(tmp_path: Path) -> None:
    source_root, destination_root = tmp_path / "source", tmp_path / "destination"
    source_root.mkdir()
    destination_root.mkdir()
    (source_root / "ok").write_text("ok")
    os.symlink("/etc/passwd", source_root / "escape")
    before = list(destination_root.iterdir())

    with pytest.raises(ValueError, match="source symlink escapes"):
        _copy(source_root, destination_root, source_root, destination_root)
    assert list(destination_root.iterdir()) == before

    (source_root / "escape").unlink()
    os.symlink("/etc", destination_root / "outside")
    with pytest.raises(ValueError, match="destination symlink escapes"):
        _copy(source_root / "ok", destination_root / "outside", source_root, destination_root)


def test_symlinks_are_preserved_only_when_their_new_target_stays_internal(tmp_path: Path) -> None:
    source_root, destination_root = tmp_path / "source", tmp_path / "destination"
    source_root.mkdir()
    destination_root.mkdir()
    (source_root / "target").write_text("ok")
    os.symlink("target", source_root / "internal")

    _copy(source_root, destination_root, source_root, destination_root)
    copied = destination_root / "internal"
    assert copied.is_symlink()
    assert os.readlink(copied) == "target"

    os.symlink("/tmp/outside", source_root / "absolute")
    with pytest.raises(ValueError):
        _copy(source_root / "absolute", destination_root / "absolute", source_root, destination_root)


def test_special_files_are_rejected_before_writes(tmp_path: Path) -> None:
    source_root, destination_root = tmp_path / "source", tmp_path / "destination"
    source_root.mkdir()
    destination_root.mkdir()
    fifo = source_root / "pipe"
    os.mkfifo(fifo)
    assert stat.S_ISFIFO(fifo.lstat().st_mode)

    with pytest.raises(ValueError, match="special files"):
        _copy(fifo, destination_root / "pipe", source_root, destination_root)
    assert not (destination_root / "pipe").exists()


@pytest.mark.asyncio
async def test_mcp_guard_passes_the_selected_scope_to_file_copy(tmp_path: Path, monkeypatch) -> None:
    source_root, destination_root = tmp_path / "source", tmp_path / "destination"
    source_root.mkdir(); destination_root.mkdir()
    (source_root / "input").write_text("ok")

    class Engine:
        def dispose(self): pass
    class Repository:
        def __init__(self, _): pass
        def get_permission_catalog_id(self, context, key): return 7 if (context, key) == ("file", "copy") else None
        def get_principal_permission_by_catalog_id(self, principal_id, catalog_id):
            return _scope(source_root, destination_root)
        def get_grants(self, definition_id):
            return [type("Grant", (), {"valid_from": datetime.now() - timedelta(seconds=1), "valid_to": datetime.now() + timedelta(seconds=1), "range": None})()]
    monkeypatch.setattr(mcp_server_module, "AuthorizationRepository", Repository)
    monkeypatch.setattr(mcp_server_module, "create_database_engine", Engine)
    monkeypatch.setattr(mcp_server_module, "create_session_factory", lambda _: object())
    token = current_principal_id.set(1)
    try:
        await create_mcp_server().call_tool("file.copy", {"source": str(source_root / "input"), "destination": str(destination_root / "output")})
    finally:
        current_principal_id.reset(token)
    assert (destination_root / "output").read_text() == "ok"
