"""Generic MCP-backed LLM tool loop."""

import json
from collections.abc import AsyncIterator
from typing import Protocol


class McpToolClient(Protocol):
    async def list_tools(self) -> list[dict[str, object]]: ...

    async def call_tool(self, name: str, arguments: dict[str, object]) -> object: ...


class ToolRunner:
    """Resolve LLM tool calls through MCP without capability knowledge."""

    def __init__(self, runtime, mcp_client_factory) -> None:
        self._runtime = runtime
        self._mcp_client_factory = mcp_client_factory

    async def stream_response(
        self, principal_id: int, messages: list[dict[str, str]], source_label: str
    ) -> AsyncIterator[str]:
        del source_label
        client = self._mcp_client_factory(principal_id)
        try:
            tools = await client.list_tools()
        except Exception as exc:
            raise RuntimeError("MCP tools/list failed.") from exc
        tool_messages: list[dict[str, object]] = list(messages)
        tool_result_cache: dict[str, object] = {}
        for _ in range(5):
            response = await self._runtime.generate_tool_response(tool_messages, tools)
            calls = response.get("tool_calls")
            if not calls:
                content = response.get("content")
                if not isinstance(content, str):
                    raise RuntimeError("Ollama returned no assistant content.")
                yield content
                return
            if not isinstance(calls, list):
                raise RuntimeError("Ollama returned invalid tool calls.")
            tool_messages.append({"role": "assistant", "content": "", "tool_calls": calls})
            for call in calls:
                name, arguments = self._parse_call(call)
                cache_key = json.dumps({"name": name, "arguments": arguments}, ensure_ascii=False, sort_keys=True)
                if cache_key not in tool_result_cache:
                    try:
                        tool_result_cache[cache_key] = await client.call_tool(name, arguments)
                    except Exception as exc:
                        raise RuntimeError("MCP tools/call failed.") from exc
                tool_messages.append(
                    {"role": "tool", "content": json.dumps(tool_result_cache[cache_key], ensure_ascii=False)}
                )
        raise RuntimeError("Tool calling exceeded five iterations.")

    @staticmethod
    def _parse_call(call: object) -> tuple[str, dict[str, object]]:
        if not isinstance(call, dict):
            raise RuntimeError("Invalid Ollama tool call.")
        function = call.get("function")
        if not isinstance(function, dict):
            raise RuntimeError("Invalid Ollama tool call.")
        name, arguments = function.get("name"), function.get("arguments")
        if not isinstance(name, str) or not isinstance(arguments, dict):
            raise RuntimeError("Invalid Ollama tool call.")
        return name, arguments
