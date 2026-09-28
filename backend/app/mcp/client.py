"""HTTP MCP client used by the production tool runner."""

import base64
import json
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from app.config import settings


Result = TypeVar("Result")


def _internal_token(principal_id: int) -> str:
    """Temporary unsigned JWT-shaped token; replace with real JWT verification."""
    def encode(value: dict[str, object]) -> str:
        return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")
    return f"{encode({'alg': 'none', 'typ': 'JWT'})}.{encode({'principal_id': principal_id})}."


class HttpMcpToolClient:
    def __init__(self, principal_id: int) -> None:
        self._principal_id = principal_id

    async def _request(self, operation: Callable[[Client], Awaitable[Result]]) -> Result:
        headers = {"Authorization": f"Bearer {_internal_token(self._principal_id)}"}
        async with httpx2.AsyncClient(headers=headers) as http:
            transport = streamable_http_client(
                f"http://{settings.api_host}:{settings.api_port}/mcp", http_client=http
            )
            async with Client(transport) as client:
                return await operation(client)

    async def list_tools(self) -> list[dict[str, object]]:
        response = await self._request(lambda client: client.list_tools())
        return [{"type": "function", "function": {"name": tool.name, "description": tool.description or "", "parameters": tool.input_schema}} for tool in response.tools]

    async def call_tool(self, name: str, arguments: dict[str, object]) -> object:
        result = await self._request(lambda client: client.call_tool(name, arguments))
        return result.model_dump(mode="json", exclude_none=True)
