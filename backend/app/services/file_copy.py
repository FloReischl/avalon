"""Safe filesystem copy operations for the ``file.copy`` capability."""

from __future__ import annotations

import os
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CopyEntry:
    source: Path
    destination: Path
    kind: str


@dataclass(frozen=True)
class FileCopyScope:
    source_root: Path
    destination_root: Path


class FileCopyService:
    """Copy files or directory contents after a complete validation preflight."""

    def copy(self, source: str, destination: str, scope: FileCopyScope) -> None:
        source_path = self._input_path(source, "source")
        destination_path = self._input_path(destination, "destination")
        entries = self._preflight(source_path, destination_path, scope)
        for entry in entries:
            self._write(entry)

    @staticmethod
    def _input_path(value: str, field: str) -> Path:
        path = Path(value).expanduser()
        if not path.is_absolute() or ".." in path.parts:
            raise ValueError(f"file.copy {field} must be an absolute path without '..'.")
        return path

    def _preflight(
        self, source: Path, destination: Path, scope: FileCopyScope
    ) -> list[CopyEntry]:
        source_root = scope.source_root.resolve(strict=True)
        destination_root = scope.destination_root.resolve(strict=True)
        if not source_root.is_dir() or not destination_root.is_dir():
            raise ValueError("file.copy scope roots must be existing directories.")
        if not source.is_relative_to(source_root) or not destination.is_relative_to(destination_root):
            raise ValueError("file.copy path is outside its authorized scope.")
        source_mode = source.lstat().st_mode
        if stat.S_ISREG(source_mode) or stat.S_ISLNK(source_mode):
            target = destination / source.name if destination.is_dir() else destination
            entries = [self._entry(source, target)]
            self._validate_entries(entries, source_root, destination_root)
            return entries
        if not stat.S_ISDIR(source_mode):
            raise ValueError("file.copy does not support special files.")

        entries = [self._entry(source, destination)]
        for path in sorted(source.rglob("*")):
            entries.append(self._entry(path, destination / path.relative_to(source)))
        self._validate_entries(entries, source_root, destination_root)
        return entries

    @staticmethod
    def _entry(source: Path, destination: Path) -> CopyEntry:
        mode = source.lstat().st_mode
        if stat.S_ISDIR(mode):
            return CopyEntry(source, destination, "directory")
        if stat.S_ISREG(mode):
            return CopyEntry(source, destination, "file")
        if stat.S_ISLNK(mode):
            return CopyEntry(source, destination, "symlink")
        raise ValueError("file.copy does not support special files.")

    @staticmethod
    def _validate_entries(
        entries: list[CopyEntry], source_root: Path, destination_root: Path
    ) -> None:
        for entry in entries:
            try:
                resolved_source = entry.source.resolve(strict=True)
            except OSError as exc:
                raise ValueError("file.copy source symlink is invalid or escapes its authorized scope.") from exc
            if not resolved_source.is_relative_to(source_root):
                raise ValueError("file.copy source symlink escapes its authorized scope.")
            effective_destination = entry.destination.resolve(strict=False)
            if not effective_destination.is_relative_to(destination_root):
                raise ValueError("file.copy destination symlink escapes its authorized scope.")
            if entry.kind == "symlink":
                link_target = Path(os.readlink(entry.source)).expanduser()
                resolved_target = (
                    link_target if link_target.is_absolute() else entry.destination.parent / link_target
                ).resolve(strict=False)
                if not resolved_target.is_relative_to(destination_root):
                    raise ValueError("file.copy copied symlink would escape its authorized scope.")
            if entry.kind == "directory" and entry.destination.exists() and not entry.destination.is_dir():
                raise ValueError("file.copy cannot merge a directory onto a non-directory.")
            if entry.kind != "directory" and entry.destination.exists() and entry.destination.is_dir():
                raise ValueError("file.copy cannot overwrite a directory with a file.")
            parent = entry.destination.parent
            while True:
                if parent.exists() and not parent.is_dir():
                    raise ValueError("file.copy destination parent is not a directory.")
                if parent == parent.parent or parent == destination_root:
                    break
                parent = parent.parent

    @staticmethod
    def _write(entry: CopyEntry) -> None:
        if entry.kind == "directory":
            entry.destination.mkdir(parents=True, exist_ok=True)
            return
        entry.destination.parent.mkdir(parents=True, exist_ok=True)
        if entry.kind == "file":
            shutil.copy2(entry.source, entry.destination)
            return
        if entry.destination.is_symlink() or entry.destination.is_file():
            entry.destination.unlink()
        elif entry.destination.exists():
            raise ValueError("file.copy cannot overwrite a directory with a symlink.")
        os.symlink(os.readlink(entry.source), entry.destination)
