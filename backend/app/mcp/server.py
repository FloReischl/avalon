"""MCP server construction for the integrated Avalon backend."""

from typing import Any

from mcp_types import CallToolResult
from mcp.server import MCPServer

from app.authorization.guard import PermissionGuard
from app.authorization.exceptions import PermissionDenied
from app.authorization.permissions import build_permission_registry
from app.authorization.runtime import get_authorization_request_manager
from app.config import settings
from app.mcp.music import register_music_tools
from app.mcp.web import register_web_tools
from app.mcp.workflow import register_workflow_tools
from app.mcp.content import register_content_tools
from app.mcp.file import register_file_tools
from app.mcp.mail import register_mail_tools
from app.persistence.music_repository import MusicRepository
from app.services.music import MusicService
from app.services.web_search import WebSearchService
from app.services.web_content import WebContentService
from app.services.audio_creation import AudioCreationService
from app.persistence.authorization_repository import AuthorizationRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.mcp.security import current_agent_id
from app.services.workflows import WorkflowService
from app.services.file_copy import FileCopyService
from app.authorization.permissions import FileCopyPermission
from app.mail.gmail import GmailMailProvider
from app.mail.manager import MailProviderManager
from app.mail.providers import MailConnectionError
from app.state import get_avalon_state


class AuthorizedMcpServer(MCPServer):
    """Central agent-based discovery and authorization for MCP tools."""

    async def list_tools(self):
        tools = await super().list_tools()
        agent_id = current_agent_id.get()
        if agent_id is None:
            return tools
        engine = create_database_engine()
        try:
            repository = AuthorizationRepository(create_session_factory(engine))
            allowed = self._permission_set_catalog_ids(agent_id, repository)
            return [
                tool
                for tool in tools
                if (resolved := self._resolve_permission(tool.name, repository)) is not None
                and resolved[2] in allowed
            ]
        finally:
            engine.dispose()

    async def call_tool(self, name: str, arguments: dict[str, Any], context=None):
        """Authorize every HTTP MCP capability call before delegation."""
        agent_id = current_agent_id.get()
        if agent_id is None:
            return await super().call_tool(name, arguments, context)
        try:
            permission_context, permission_key = name.split(".", 1)
        except ValueError as exc:
            raise ValueError(f"MCP tool {name!r} has no permission mapping.") from exc

        engine = create_database_engine()
        try:
            repository = AuthorizationRepository(create_session_factory(engine))
            resolved = self._resolve_permission(name, repository)
            if resolved is None:
                raise PermissionDenied(f"{name} is not grantable for agent.")
            permission_context, permission_key, permission_catalog_id = resolved
            registry = build_permission_registry()
            permission = registry.get(permission_context, permission_key)
            guard = PermissionGuard(
                repository,
                registry,
                get_authorization_request_manager(),
            )
            items = permission.items(arguments)
            capability = super().call_tool

            async def authorized_capability(approved_items: list[object]):
                approved_arguments = permission.approved_arguments(approved_items, arguments)
                if approved_arguments is None:
                    return CallToolResult(content=[])
                if name == "file.copy":
                    assert isinstance(permission, FileCopyPermission)
                    definition = repository.get_permission_set_by_catalog_id(
                        agent_id, permission_catalog_id
                    )
                    assert definition is not None
                    scope = permission.scope_for(definition, approved_items)
                    if scope is None:
                        raise PermissionDenied("file.copy is not allowed by agent scope.")
                    self._file_copy_service.copy(
                        approved_arguments["source"], approved_arguments["destination"], scope
                    )
                    return CallToolResult(content=[])
                return await capability(name, approved_arguments, context)

            return await guard.execute(
                agent_id,
                permission_context,
                permission_key,
                items,
                authorized_capability,
                "MCP",
                permission_catalog_id=permission_catalog_id,
            )
        finally:
            engine.dispose()

    def _permission_set_catalog_ids(
        self, agent_id: int, repository: AuthorizationRepository
    ) -> set[int]:
        if not hasattr(self, "_permission_set_cache"):
            self._permission_set_cache: dict[int, set[int]] = {}
        cache = self._permission_set_cache
        if agent_id not in cache:
            cache[agent_id] = repository.get_permission_set_catalog_ids(agent_id)
        return cache[agent_id]

    @staticmethod
    def _resolve_permission(
        name: str, repository: AuthorizationRepository
    ) -> tuple[str, str, int] | None:
        if name.startswith("mail."):
            permission_catalog_id = repository.get_permission_catalog_id("mail", "read")
            return (
                ("mail", "read", permission_catalog_id)
                if permission_catalog_id is not None
                else None
            )
        try:
            context, key = name.split(".", 1)
        except ValueError:
            return None
        permission_catalog_id = repository.get_permission_catalog_id(context, key)
        if permission_catalog_id is None:
            return None
        return context, key, permission_catalog_id


def create_mcp_server(
    service: MusicService | None = None,
    web_search_service: WebSearchService | None = None,
    web_content_service: WebContentService | None = None,
    workflow_service: WorkflowService | None = None,
    audio_creation_service: AudioCreationService | None = None,
    file_copy_service: FileCopyService | None = None,
    mail_manager: MailProviderManager | None = None,
) -> MCPServer:
    """Create the MCP server mounted by the FastAPI backend."""
    mcp = AuthorizedMcpServer("Avalon Backend")
    register_music_tools(
        mcp,
        service or MusicService(MusicRepository(settings.music_db_path)),
    )
    register_web_tools(
        mcp,
        web_search_service or WebSearchService(),
        web_content_service or WebContentService(),
    )
    register_workflow_tools(mcp, workflow_service or WorkflowService())
    register_content_tools(mcp, audio_creation_service or AudioCreationService())
    mcp._file_copy_service = file_copy_service or FileCopyService()  # type: ignore[attr-defined]
    register_file_tools(mcp, mcp._file_copy_service)  # type: ignore[attr-defined]
    if mail_manager is None:
        def gmail_provider() -> GmailMailProvider:
            config = get_avalon_state().user_config.mail
            if config is None:
                raise MailConnectionError("Gmail mail configuration is missing.")
            return GmailMailProvider(config.google)

        mail_manager = MailProviderManager(get_avalon_state, {"gmail": gmail_provider})
    register_mail_tools(mcp, mail_manager)
    return mcp
