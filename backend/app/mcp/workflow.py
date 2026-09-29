"""Thin MCP tool registration for registered workflow execution."""

import json
import logging

from mcp.server import MCPServer
from pydantic import JsonValue

from app.services.workflows import WorkflowService


logger = logging.getLogger(__name__)


def register_workflow_tools(mcp: MCPServer, service: WorkflowService) -> None:
    """Register workflow tools that delegate to the workflow application service."""

    @mcp.tool(name="workflow.execute")
    async def execute(workflow_key: str, payload: JsonValue) -> None:
        """Execute one registered workflow with a JSON payload."""
        logger.info(
            "tool=workflow.execute request=%s",
            json.dumps(
                {"workflow_key": workflow_key, "payload": payload},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        )
        await service.execute(workflow_key, payload)
