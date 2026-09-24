"""Minimal in-process LLM tool runner for the first capability slice."""

import json
from collections.abc import AsyncIterator, Callable
from typing import Awaitable

from app.authorization.guard import PermissionGuard
from app.runtime.ollama import OllamaRuntime
from app.services.web_search import WebSearchService


WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web.search",
        "description": "Durchsuche das Web bei DuckDuckGo nach aktuellen Informationen.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
}


class ToolRunner:
    """Resolve Ollama tool calls without exposing authorization to the LLM."""

    def __init__(self, runtime: OllamaRuntime, guard: PermissionGuard, web: WebSearchService) -> None:
        self._runtime = runtime
        self._guard = guard
        self._web = web

    async def stream_response(
        self, principal_id: int, messages: list[dict[str, str]], source_label: str
    ) -> AsyncIterator[str]:
        tool_messages: list[dict[str, object]] = list(messages)
        for _ in range(5):
            response = await self._runtime.generate_tool_response(
                tool_messages, [WEB_SEARCH_TOOL]
            )
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
                result = await self._run_call(principal_id, call, source_label)
                tool_messages.append(
                    {"role": "tool", "content": json.dumps(result, ensure_ascii=False)}
                )
        raise RuntimeError("Tool calling exceeded five iterations.")

    async def _run_call(self, principal_id: int, call: object, source_label: str) -> list[dict[str, str]]:
        if not isinstance(call, dict) or call.get("function", {}).get("name") != "web.search":
            raise RuntimeError("Unsupported Ollama tool call.")
        arguments = call["function"].get("arguments")
        if not isinstance(arguments, dict) or not isinstance(arguments.get("query"), str):
            raise RuntimeError("web.search requires a string query.")
        items: list[object] = [{"query": arguments["query"]}]

        async def capability(approved: list[object]) -> list[dict[str, str]]:
            if not approved:
                return []
            query = approved[0]
            assert isinstance(query, dict)
            return await self._web.search(query["query"])

        return await self._guard.execute(
            principal_id, "web", "search", items, capability, source_label
        )
