"""MCP registration for read-only mail capabilities."""

import base64
from datetime import datetime, timezone
from typing import Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from app.mail.manager import MailProviderManager
from app.mail.models import Mail, MailAttachmentResponse, MailMessage, MailProviderStats
from app.mail.providers import MailError


def register_mail_tools(mcp: MCPServer, manager: MailProviderManager) -> None:
    """Register mail capabilities."""

    @mcp.tool(name="mail.set_provider")
    async def set_provider(provider: Literal["gmail", "mailbox"]) -> None:
        manager.set_provider(provider)

    @mcp.tool(name="mail.get_provider_stats")
    async def get_provider_stats() -> MailProviderStats:
        return manager.get_provider_stats()

    @mcp.tool(name="mail.get_messages")
    async def get_messages(
        category: str,
        since: datetime | None = None,
        before: datetime | None = None,
    ) -> list[MailMessage]:
        since = _utc_timestamp(since)
        before = _utc_timestamp(before if before is not None else _current_local_time())
        if since is not None and before is not None and since >= before:
            raise ValueError("since must be earlier than before.")
        return manager.get_messages(category, since, before)

    @mcp.tool(name="mail.get_messages_by_thread")
    async def get_messages_by_thread(thread_id: str) -> list[MailMessage]:
        if not thread_id.strip():
            raise ValueError("thread_id must not be empty.")
        return manager.get_messages_by_thread(thread_id)

    @mcp.tool(name="mail.get_mail")
    async def get_mail(message_id: str, as_text: bool = True) -> Mail:
        """Get one mail with its preferred body, as LLM-friendly plaintext by default."""
        return manager.get_mail(message_id, as_text)

    @mcp.tool(name="mail.get_attachment")
    async def get_attachment(message_id: str, attachment_id: str) -> MailAttachmentResponse:
        """Get one mail attachment as Base64-encoded binary content."""
        try:
            attachment = manager.get_attachment(message_id, attachment_id)
        except MailError as exc:
            raise ToolError(str(exc)) from exc
        return MailAttachmentResponse(
            file_name=attachment.file_name,
            mime_type=attachment.mime_type,
            content_base64=base64.b64encode(attachment.content).decode("ascii"),
        )

    @mcp.tool(name="mail.get_categories")
    async def get_categories() -> list[str]:
        return manager.get_categories()

    @mcp.tool(name="mail.create_categories")
    async def create_categories(categories: list[str]) -> None:
        manager.create_categories(categories)

    @mcp.tool(name="mail.set_categories")
    async def set_categories(message_id: str, categories: list[str], archive: bool = False) -> None:
        manager.set_categories(message_id, categories, archive)

    @mcp.tool(name="mail.unset_categories")
    async def unset_categories(message_id: str, categories: list[str]) -> None:
        manager.unset_categories(message_id, categories)


def _current_local_time() -> datetime:
    """Return the current system-local timestamp as an aware datetime."""
    return datetime.now().astimezone()


def _utc_timestamp(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc)
