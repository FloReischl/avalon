"""Tests for immutable attachment persistence and copy-in storage."""

from pathlib import Path

import pytest
from fastapi import UploadFile
from sqlalchemy import func, select

from app.persistence.attachment_repository import AttachmentRepository
from app.persistence.chat_repository import ChatRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.persistence.migrations import run_migrations
from app.persistence.models import Attachment
from app.services.attachments import (
    FALLBACK_MIME_TYPE,
    AttachmentService,
    AttachmentTooLargeError,
    MAX_ATTACHMENT_SIZE,
    _detect_mime_type,
)


@pytest.fixture
def attachment_service(tmp_path: Path):
    database_path = tmp_path / "avalon.sqlite"
    run_migrations(database_path)
    engine = create_database_engine(database_path)
    session_factory = create_session_factory(engine)
    chat_repository = ChatRepository(session_factory)
    chat = chat_repository.create_chat_with_message("Chat", "user", "Hallo")
    message_id = chat_repository.get_messages(chat.id)[0].id
    try:
        yield (
            AttachmentService(
                AttachmentRepository(session_factory), tmp_path / "attachments"
            ),
            chat_repository,
            session_factory,
            message_id,
            chat.id,
            tmp_path / "attachments",
        )
    finally:
        engine.dispose()


def upload(filename: str, content: bytes) -> UploadFile:
    from io import BytesIO

    return UploadFile(filename=filename, file=BytesIO(content))


@pytest.mark.asyncio
async def test_upload_copies_file_and_persists_detected_metadata(attachment_service) -> None:
    service, _, _, message_id, _, storage = attachment_service

    attachment = await service.upload_for_message(
        message_id, upload("report.txt", b"Avalon attachment")
    )

    assert attachment is not None
    assert attachment.original_file_name == "report.txt"
    assert attachment.mime_type == "text/plain"
    assert attachment.size == len(b"Avalon attachment")
    assert attachment.file_name != attachment.original_file_name
    assert (storage / attachment.file_name).read_bytes() == b"Avalon attachment"


@pytest.mark.asyncio
async def test_upload_keeps_only_client_basename(attachment_service) -> None:
    service, _, _, message_id, _, _ = attachment_service

    attachment = await service.upload_for_message(
        message_id, upload(r"C:\\Users\\Flo\\report.txt", b"content")
    )

    assert attachment is not None
    assert attachment.original_file_name == "report.txt"


def test_mime_detection_falls_back_when_file_utility_fails(monkeypatch, tmp_path: Path) -> None:
    import app.services.attachments as attachments_module

    def fail(*args, **kwargs):
        raise OSError("file is unavailable")

    monkeypatch.setattr(attachments_module.subprocess, "run", fail)

    assert _detect_mime_type(tmp_path / "missing") == FALLBACK_MIME_TYPE


@pytest.mark.asyncio
async def test_every_import_creates_a_distinct_attachment(attachment_service) -> None:
    service, _, _, message_id, _, storage = attachment_service

    first = await service.upload_for_message(message_id, upload("same.bin", b"same"))
    second = await service.upload_for_message(message_id, upload("same.bin", b"same"))

    assert first is not None and second is not None
    assert first.id != second.id
    assert first.file_name != second.file_name
    assert len(list(storage.iterdir())) == 2


@pytest.mark.asyncio
async def test_oversized_upload_is_not_persisted(attachment_service) -> None:
    service, _, session_factory, message_id, _, storage = attachment_service

    with pytest.raises(AttachmentTooLargeError):
        await service.upload_for_message(
            message_id, upload("large.bin", b"x" * (MAX_ATTACHMENT_SIZE + 1))
        )

    assert not storage.exists() or list(storage.iterdir()) == []
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Attachment)) == 0


@pytest.mark.asyncio
async def test_message_deletion_keeps_attachment_and_storage(attachment_service) -> None:
    service, chat_repository, _, message_id, chat_id, storage = attachment_service
    attachment = await service.upload_for_message(message_id, upload("keep.dat", b"keep"))
    assert attachment is not None
    assert chat_repository.delete_chat(chat_id) is True
    assert service.get(attachment.id) is not None
    assert (storage / attachment.file_name).is_file()
