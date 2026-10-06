"""Live, opt-in compatibility checks for Avalon's local Ollama models.

These tests deliberately exercise the native ``/api/chat`` tool-call envelope.
They do not contact DuckDuckGo or wait for an authorization decision: the
ToolRunner path receives an in-process grant and a deterministic search result.
"""

import json
import os
from types import SimpleNamespace

import httpx
import pytest

from app.config import settings
from app.runtime.ollama import OllamaRuntime
from app.services.tool_runner import ToolRunner


pytestmark = pytest.mark.integration

_RUN_ENVIRONMENT_VARIABLE = "AVALON_RUN_TOOL_CALL_INTEGRATION"
_MODELS = (
    "qwen2.5-coder:14b-instruct-ctx16k",
    "qwen2.5-coder:7b-instruct-ctx16k",
    "gemma4:e4b-it-q4_K_M-ctx16k",
)
_QWEN_MODELS = _MODELS[:2]
_QWEN_TOOL_LOOP_CASES = (
    pytest.param(_QWEN_MODELS[0], id="qwen-14b"),
    *(
        pytest.param(_QWEN_MODELS[1], id=f"qwen-7b-run-{run}")
        for run in range(1, 6)
    ),
)
_TOOL_QUERY = "Avalon Tool Calling Integration Test"
_FAKE_RESULT_TITLE = "Avalon Tool-Test"
_TOOL_PROMPT = (
    "Rufe zwingend genau einmal das Tool web.search mit der Query "
    f"'{_TOOL_QUERY}' auf. Nachdem du das Ergebnis erhalten hast, antworte in "
    "einem kurzen vollständigen deutschen Satz, der dessen Titel nennt. Gib "
    "niemals JSON oder das unveränderte Toolresultat aus."
)
_WEB_SEARCH_TOOL = {"type": "function", "function": {"name": "web.search", "description": "", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}}


def _integration_enabled() -> bool:
    return os.environ.get(_RUN_ENVIRONMENT_VARIABLE) == "1"


def _runtime_for(model: str) -> OllamaRuntime:
    state = SimpleNamespace(
        current_llm=SimpleNamespace(model=model),
        llm_switch_active=False,
        begin_llm_inference=lambda: None,
        end_llm_inference=lambda: None,
    )
    return OllamaRuntime(lambda: state)


class _TracingToolRuntime:
    """Print each tool-loop exchange when pytest output capture is disabled."""

    def __init__(self, model: str, runtime: OllamaRuntime) -> None:
        self._model = model
        self._runtime = runtime
        self._step = 0

    async def generate_tool_response(self, messages, tools) -> dict[str, object]:
        self._step += 1
        print(
            f"\\n[{self._model} tool-loop step {self._step}] request messages:\\n"
            f"{json.dumps(messages, ensure_ascii=False, indent=2)}"
        )
        response = await self._runtime.generate_tool_response(messages, tools)
        print(
            f"[{self._model} tool-loop step {self._step}] response:\\n"
            f"{json.dumps(response, ensure_ascii=False, indent=2)}"
        )
        return response


async def _stop_active_ollama_models() -> None:
    """Unload every model currently resident in Ollama before one heavy test."""
    ollama_url = f"http://{settings.ollama_host}"
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(f"{ollama_url}/api/ps")
        response.raise_for_status()
        models = response.json().get("models")
        if not isinstance(models, list):
            raise AssertionError("Ollama /api/ps returned no model list.")

        for loaded_model in models:
            if not isinstance(loaded_model, dict):
                raise AssertionError("Ollama /api/ps returned an invalid model entry.")
            name = loaded_model.get("name")
            if not isinstance(name, str) or not name:
                raise AssertionError("Ollama /api/ps returned a model without a name.")
            unload_response = await client.post(
                f"{ollama_url}/api/generate",
                json={"model": name, "keep_alive": 0},
            )
            unload_response.raise_for_status()


def _assert_expected_call(response: dict[str, object], model: str) -> None:
    calls = response.get("tool_calls")
    assert isinstance(calls, list) and len(calls) == 1, (
        f"{model} did not return exactly one native tool call: {response!r}"
    )
    function = calls[0].get("function") if isinstance(calls[0], dict) else None
    assert isinstance(function, dict), f"{model} returned an invalid tool call: {calls[0]!r}"
    assert function.get("name") == "web.search"
    assert function.get("arguments") == {"query": _TOOL_QUERY}


@pytest.mark.asyncio
@pytest.mark.parametrize("model", _MODELS, ids=("qwen-14b", "qwen-7b", "gemma"))
async def test_model_returns_tool_call_through_ollama_runtime(model: str) -> None:
    if not _integration_enabled():
        pytest.skip(f"set {_RUN_ENVIRONMENT_VARIABLE}=1 to run local Ollama model checks")

    await _stop_active_ollama_models()
    response = await _runtime_for(model).generate_tool_response(
        [{"role": "user", "content": _TOOL_PROMPT}], [_WEB_SEARCH_TOOL]
    )

    _assert_expected_call(response, model)


class _FakeMcpClient:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def list_tools(self):
        return [_WEB_SEARCH_TOOL]

    async def call_tool(self, name, arguments) -> list[dict[str, str]]:
        assert (name, arguments) == ("web.search", {"query": _TOOL_QUERY})
        self.queries.append(arguments["query"])
        return [
            {
                "title": _FAKE_RESULT_TITLE,
                "url": "https://example.test/avalon-tool-test",
                "snippet": "Dieses Ergebnis stammt nicht aus einer echten Websuche.",
            }
        ]


@pytest.mark.asyncio
@pytest.mark.parametrize("model", _QWEN_TOOL_LOOP_CASES)
async def test_qwen_text_json_fallback_completes_tool_runner_loop(model: str) -> None:
    """Prove Qwen's text-JSON fallback drives the production tool loop."""
    if not _integration_enabled():
        pytest.skip(f"set {_RUN_ENVIRONMENT_VARIABLE}=1 to run local Ollama model checks")

    await _stop_active_ollama_models()
    mcp = _FakeMcpClient()
    runner = ToolRunner(
        _TracingToolRuntime(model, _runtime_for(model)),
        lambda agent_id: mcp,
    )

    answer = "".join(
        [
            chunk
            async for chunk in runner.stream_response(
                42,
                [{"role": "user", "content": _TOOL_PROMPT}],
                "Tool-call integration test",
            )
        ]
    )

    assert mcp.queries == [_TOOL_QUERY], f"{model} did not execute the parsed tool call."
    assert answer.strip(), f"{model} produced no final response after the tool result."
    assert _FAKE_RESULT_TITLE in answer
    assert not answer.lstrip().startswith(("{", "[")), (
        f"{model} returned the raw tool result instead of a natural-language answer."
    )

if __name__ == "__main__":
    os.environ["AVALON_RUN_TOOL_CALL_INTEGRATION"] = "1"

    # Führt alle Tests in genau dieser Datei aus (__file__)
    pytest.main([__file__, "-k", "test_qwen_text_json_fallback_completes_tool_runner_loop", "-v", "-s", "--capture=no" ])
