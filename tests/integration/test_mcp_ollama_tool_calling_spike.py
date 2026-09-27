"""Opt-in MCP-to-Ollama tool-calling compatibility spike.

Run the already running Avalon backend and then execute::

    AVALON_RUN_MCP_SPIKE=1 ./.venv/bin/python -m pytest -m mcp_spike -v -s

The tool schema intentionally comes from MCP ``tools/list``.  This spike does
not use ``WEB_SEARCH_TOOL`` or ``ToolRunner`` because it verifies the boundary
between an MCP client and a local model directly.
"""

import json
import os
import socket
from types import SimpleNamespace
from typing import Any

import pytest
from mcp import Client

import app.runtime.ollama as ollama_module
from app.config import settings
from app.runtime.ollama import OllamaRuntime


pytestmark = [pytest.mark.integration, pytest.mark.mcp_spike]

_RUN_ENVIRONMENT_VARIABLE = "AVALON_RUN_MCP_SPIKE"
_MODELS = (
    "qwen2.5-coder:7b-instruct-ctx16k",
    "qwen2.5-coder:14b-instruct-ctx16k",
    "gemma4:e4b-it-q4_K_M-ctx16k",
)
_QUERY = "Avalon MCP Tool Calling Spike eindeutige Testsuche"
_PROMPT = (
    "Du musst zur Beantwortung zwingend genau einmal das Tool web.search mit "
    f"der Query '{_QUERY}' aufrufen. Nach dem Toolresultat antworte bitte mit "
    "einem kurzen natürlichen deutschen Satz. Gib weder JSON noch einen "
    "weiteren Toolaufruf aus."
)
_MCP_URL = f"http://{settings.api_host}:{settings.api_port}/mcp"


def _enabled() -> bool:
    return os.environ.get(_RUN_ENVIRONMENT_VARIABLE) == "1"


def _mcp_server_available() -> bool:
    try:
        with socket.socket() as connection:
            return connection.connect_ex((settings.api_host, settings.api_port)) == 0
    except OSError:
        return False


def _runtime_for(model: str) -> OllamaRuntime:
    state = SimpleNamespace(
        current_llm=SimpleNamespace(model=model),
        llm_switch_active=False,
        begin_llm_inference=lambda: None,
        end_llm_inference=lambda: None,
    )
    return OllamaRuntime(lambda: state)


def _tool_to_ollama_definition(tool: Any) -> dict[str, object]:
    """Translate the MCP Tool returned by ``tools/list`` to Ollama's shape."""
    name = getattr(tool, "name", None)
    # MCP's wire key is ``inputSchema``; the Python client exposes the
    # Pydantic field as ``input_schema``.
    schema = getattr(tool, "input_schema", None)
    description = getattr(tool, "description", None)
    if not isinstance(name, str) or not name:
        raise AssertionError(f"MCP returned a tool without a valid name: {tool!r}")
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise AssertionError(f"MCP tool {name!r} has no compatible object schema: {schema!r}")
    if not isinstance(description, str):
        description = ""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": schema,
        },
    }


def _assert_web_search_call(response: dict[str, object], model: str) -> dict[str, object]:
    calls = response.get("tool_calls")
    assert isinstance(calls, list) and len(calls) == 1, (
        f"{model} did not return exactly one tool call: {response!r}"
    )
    call = calls[0]
    assert isinstance(call, dict), f"{model} returned an invalid tool call: {call!r}"
    function = call.get("function")
    assert isinstance(function, dict), f"{model} returned an invalid function: {call!r}"
    assert function.get("name") == "web.search", f"{model} selected {function.get('name')!r}"
    assert function.get("arguments") == {"query": _QUERY}, (
        f"{model} returned invalid web.search arguments: {function.get('arguments')!r}"
    )
    return call


def _call_key(call: dict[str, object]) -> str:
    function = call["function"]
    assert isinstance(function, dict)
    return json.dumps(function, ensure_ascii=False, sort_keys=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("model", _MODELS, ids=("qwen-7b", "qwen-14b", "gemma4"))
async def test_mcp_web_search_round_trip_with_local_model(
    model: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise MCP list/call, Ollama tool calling, and one final model answer."""
    if not _enabled():
        pytest.skip(f"set {_RUN_ENVIRONMENT_VARIABLE}=1 to run this live MCP spike")
    if not _mcp_server_available():
        pytest.skip(f"requires a running Avalon MCP server at {_MCP_URL}")

    runtime = _runtime_for(model)
    if not await runtime.model_exists(model):
        pytest.skip(f"required local Ollama model is unavailable (no download attempted): {model}")

    raw_responses: list[dict[str, object]] = []
    original_normalizer = ollama_module._normalize_qwen_text_tool_call

    def trace_normalization(raw_model: str, message: dict[str, object]) -> dict[str, object]:
        raw_responses.append(dict(message))
        return original_normalizer(raw_model, message)

    monkeypatch.setattr(ollama_module, "_normalize_qwen_text_tool_call", trace_normalization)

    async with Client(_MCP_URL) as client:
        tools_response = await client.list_tools()
        tools = getattr(tools_response, "tools", None)
        assert isinstance(tools, list), f"MCP tools/list returned no tool list: {tools_response!r}"
        web_tool = next((tool for tool in tools if getattr(tool, "name", None) == "web.search"), None)
        assert web_tool is not None, "MCP tools/list did not expose web.search"
        ollama_tool = _tool_to_ollama_definition(web_tool)
        print(f"\n[{model}] MCP tools/list web.search schema:\n{json.dumps(ollama_tool, ensure_ascii=False, indent=2)}")

        messages: list[dict[str, object]] = [{"role": "user", "content": _PROMPT}]
        executed_calls: dict[str, str] = {}
        for step in range(1, 6):
            response = await runtime.generate_tool_response(messages, [ollama_tool])
            raw_response = raw_responses[-1]
            response_kind = (
                "no tool call"
                if not response.get("tool_calls")
                else "Qwen text-JSON fallback"
                if raw_response.get("tool_calls") is None
                else "native tool_calls"
            )
            print(f"[{model}] Ollama step {step} ({response_kind}):\n{json.dumps(response, ensure_ascii=False, indent=2)}")
            calls = response.get("tool_calls")
            if not calls:
                content = response.get("content")
                assert isinstance(content, str) and content.strip(), (
                    f"{model} produced no final assistant response: {response!r}"
                )
                assert not content.lstrip().startswith(("{", "[")), (
                    f"{model} returned JSON instead of a natural-language final response: {content!r}"
                )
                assert step > 1, f"{model} answered without calling web.search"
                print(f"[{model}] final answer: {content}")
                return

            call = _assert_web_search_call(response, model)
            key = _call_key(call)
            messages.append({"role": "assistant", "content": "", "tool_calls": [call]})
            if key not in executed_calls:
                function = call["function"]
                assert isinstance(function, dict)
                result = await client.call_tool("web.search", function["arguments"])
                assert result.is_error is False, f"MCP tools/call failed: {result!r}"
                result_content = json.dumps(
                    result.model_dump(mode="json", exclude_none=True), ensure_ascii=False
                )
                executed_calls[key] = result_content
                print(f"[{model}] MCP tools/call web.search result: {result_content}")
            else:
                print(f"[{model}] repeated identical web.search call; reusing prior MCP result")
            messages.append({"role": "tool", "content": executed_calls[key]})

    pytest.fail(f"{model} repeated tool calls without producing a final answer")
