"""Generic MCP-backed LLM tool loop."""

import json
from collections.abc import AsyncIterator
from typing import Protocol


class McpToolClient(Protocol):
    async def list_tools(self) -> list[dict[str, object]]: ...

    async def call_tool(self, name: str, arguments: dict[str, object]) -> object: ...


class ToolRunner:
    """Resolve LLM tool calls through MCP without capability knowledge."""

    _tool_definition_cache: dict[int, list[dict[str, object]]] = {}

    def __init__(self, runtime, mcp_client_factory) -> None:
        self._runtime = runtime
        self._mcp_client_factory = mcp_client_factory

    async def stream_response(
        self, agent_id: int, messages: list[dict[str, str]], source_label: str, chat_id: int
    ) -> AsyncIterator[str]:
        del source_label
        client = self._mcp_client_factory(agent_id, chat_id)
        tools = await self._tools_for_agent(agent_id, client)
        tool_messages: list[dict[str, object]] = list(messages)
        tool_result_cache: dict[str, object] = {}
        for _ in range(5):
            content_chunks: list[str] = []
            calls: list[object] = []

            async for response in self._runtime.generate_tool_response_stream(
                tool_messages, tools
            ):
                content = response.get("content")
                if content is not None and not isinstance(content, str):
                    raise RuntimeError("Ollama returned invalid assistant content.")
                if content:
                    content_chunks.append(content)
                    yield content

                response_calls = response.get("tool_calls")
                if response_calls is not None:
                    if not isinstance(response_calls, list):
                        raise RuntimeError("Ollama returned invalid tool calls.")
                    calls.extend(response_calls)

            if not calls:
                if not content_chunks:
                    raise RuntimeError("Ollama returned no assistant content.")
                return

            tool_messages.append(
                {
                    "role": "assistant",
                    "content": "".join(content_chunks),
                    "tool_calls": calls,
                }
            )
            for call in calls:
                name, arguments = self._parse_call(call)
                cache_key = json.dumps(
                    {"name": name, "arguments": arguments},
                    ensure_ascii=False,
                    sort_keys=True,
                )
                if cache_key not in tool_result_cache:
                    try:
                        tool_result_cache[cache_key] = await client.call_tool(
                            name, arguments
                        )
                    except Exception as exc:
                        raise RuntimeError("MCP tools/call failed.") from exc
                tool_messages.append(
                    {
                        "role": "tool",
                        "content": json.dumps(
                            tool_result_cache[cache_key], ensure_ascii=False
                        ),
                    }
                )
        raise RuntimeError("Tool calling exceeded five iterations.")

    @classmethod
    async def _tools_for_agent(
        cls, agent_id: int, client: McpToolClient
    ) -> list[dict[str, object]]:
        if agent_id not in cls._tool_definition_cache:
            try:
                cls._tool_definition_cache[agent_id] = await client.list_tools()
            except Exception as exc:
                raise RuntimeError("MCP tools/list failed.") from exc
        return cls._tool_definition_cache[agent_id]

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
