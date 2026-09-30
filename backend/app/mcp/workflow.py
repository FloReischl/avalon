"""Thin MCP tool registration for registered workflow execution."""

import json
import logging

from mcp.server import MCPServer
from mcp.server.mcpserver.context import Context
from pydantic import JsonValue

from app.config import settings
from app.mcp.security import current_principal_id
from app.services.workflows import WorkflowService


logger = logging.getLogger(__name__)


def register_workflow_tools(mcp: MCPServer, service: WorkflowService) -> None:
    """Register workflow tools that delegate to the workflow application service."""

    @mcp.tool(name="workflow.execute")
    async def execute(workflow_key: str, payload: JsonValue, ctx: Context) -> dict[str, int]:
        """Execute one registered workflow with a JSON payload."""
        logger.info(
            "tool=workflow.execute request=%s",
            json.dumps(
                {"workflow_key": workflow_key, "payload": payload},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        )
        meta = ctx.request_context.meta or {}
        execution_context = meta.get("avalon/execution_context")
        if (
            not isinstance(execution_context, dict)
            or not isinstance(execution_context.get("chat_id"), int)
            or not isinstance(execution_context.get("invocation_id"), str)
        ):
            raise ValueError("workflow.execute requires Avalon execution context.")
        execution_id = await service.execute(
            workflow_key,
            payload,
            execution_context["chat_id"],
            execution_context["invocation_id"],
            f"http://{settings.api_host}:{settings.api_port}",
            current_principal_id.get(),
        )
        return {"workflow_execution_id": execution_id}
