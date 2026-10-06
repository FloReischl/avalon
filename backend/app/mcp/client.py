"""HTTP MCP client used by the production tool runner."""

import uuid
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from app.config import settings
from app.mcp.security import bearer_token_for_agent


Result = TypeVar("Result")


class HttpMcpToolClient:
    _REQUEST_TIMEOUT_SECONDS = 60 * 60

    def __init__(self, agent_id: int, chat_id: int | None = None) -> None:
        self._agent_id = agent_id
        self._chat_id = chat_id
        self._invocation_id = str(uuid.uuid4())

    async def _request(self, operation: Callable[[Client], Awaitable[Result]]) -> Result:
        headers = {"Authorization": f"Bearer {bearer_token_for_agent(self._agent_id)}"}
        async with httpx2.AsyncClient(
            headers=headers, timeout=self._REQUEST_TIMEOUT_SECONDS
        ) as http:
            transport = streamable_http_client(
                f"http://{settings.api_host}:{settings.api_port}/mcp", http_client=http
            )
            async with Client(transport) as client:
                return await operation(client)

    async def list_tools(self) -> list[dict[str, object]]:
        response = await self._request(lambda client: client.list_tools())
        return [{"type": "function", "function": {"name": tool.name, "description": tool.description or "", "parameters": tool.input_schema}} for tool in response.tools]

    async def call_tool(self, name: str, arguments: dict[str, object]) -> object:
        meta = None if self._chat_id is None else {
            "avalon/execution_context": {
                "chat_id": self._chat_id,
                "invocation_id": self._invocation_id,
            }
        }
        result = await self._request(lambda client: client.call_tool(name, arguments, meta=meta))
        return result.model_dump(mode="json", exclude_none=True)
