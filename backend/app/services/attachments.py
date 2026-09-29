"""Copy-in storage for Avalon attachment artifacts."""

import subprocess
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.persistence.attachment_repository import AttachmentRepository
from app.persistence.models import Attachment


MAX_ATTACHMENT_SIZE = 50 * 1024 * 1024
FALLBACK_MIME_TYPE = "application/octet-stream"


class AttachmentTooLargeError(ValueError):
    """Raised when an uploaded file exceeds Avalon's V1 limit."""


def _client_basename(filename: str) -> str:
    """Keep only the basename from either common client path syntax."""
    return filename.replace("\\", "/").rsplit("/", 1)[-1]


def _detect_mime_type(path: Path) -> str:
    """Determine MIME type from copied file content using the local file utility."""
    try:
        result = subprocess.run(
            ["file", "--brief", "--mime-type", "--", str(path)],
            capture_output=True,
            check=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return FALLBACK_MIME_TYPE

    mime_type = result.stdout.strip()
    return mime_type if "/" in mime_type else FALLBACK_MIME_TYPE


class AttachmentService:
    """Create immutable attachment artifacts through copy-in storage."""

    def __init__(
        self,
        repository: AttachmentRepository,
        storage_directory: Path | None = None,
    ) -> None:
        self._repository = repository
        self._storage_directory = storage_directory or Path.home() / ".avalon" / "attachments"

    async def upload_for_message(
        self, message_id: int, upload: UploadFile
    ) -> Attachment | None:
        """Copy one upload into storage and persist it with its relation."""
        original_file_name = _client_basename(upload.filename or "")
        if not original_file_name:
            raise ValueError("Attachment filename must not be empty.")

        suffix = Path(original_file_name).suffix
        file_name = f"{uuid4()}{suffix}"
        target = self._storage_directory / file_name
        self._storage_directory.mkdir(parents=True, exist_ok=True)
        size = 0
        try:
            with target.open("xb") as destination:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_ATTACHMENT_SIZE:
                        raise AttachmentTooLargeError()
                    destination.write(chunk)

            attachment = self._repository.create_and_attach(
                message_id=message_id,
                file_name=file_name,
                original_file_name=original_file_name,
                mime_type=_detect_mime_type(target),
                size=size,
            )
            if attachment is not None:
                return attachment
        except Exception:
            target.unlink(missing_ok=True)
            raise

        target.unlink(missing_ok=True)
        return None

    def path_for(self, attachment: Attachment) -> Path:
        """Resolve a persisted attachment to its fixed Avalon storage path."""
        return self._storage_directory / attachment.file_name

    def get(self, attachment_id: int) -> Attachment | None:
        """Return persisted attachment metadata by id."""
        return self._repository.get(attachment_id)
