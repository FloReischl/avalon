"""MCP registration for read-only mail capabilities."""

from datetime import datetime
from typing import Literal

from mcp.server import MCPServer

from app.mail.manager import MailProviderManager
from app.mail.models import MailMessage, MailProviderStats


def register_mail_tools(mcp: MCPServer, manager: MailProviderManager) -> None:
    """Register the AP1 read-only mail surface."""

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
        if since is not None and before is not None and since >= before:
            raise ValueError("since must be earlier than before.")
        return manager.get_messages(category, since, before)

    @mcp.tool(name="mail.get_messages_by_thread")
    async def get_messages_by_thread(thread_id: str) -> list[MailMessage]:
        if not thread_id.strip():
            raise ValueError("thread_id must not be empty.")
        return manager.get_messages_by_thread(thread_id)
