"""Small client SDK for Avalon workflow scripts."""

from __future__ import annotations

import json
import sys
from typing import Any

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client


class AvalonWorkflowClient:
    """Thin client around the Avalon APIs exposed to workflow scripts."""

    def __init__(
        self,
        envelope: dict[str, Any],
        *,
        timeout: float = 60 * 60,
    ) -> None:
        avalon = envelope["avalon"]

        self.payload = envelope.get("payload")
        self.backend_url = str(avalon["backend_url"]).rstrip("/")
        self.workflow_execution_id = int(avalon["workflow_execution_id"])
        self.bearer_token = str(avalon["bearer_token"])
        self.model_persona = avalon.get("model_persona")
        self.model_instructions = avalon.get("model_instructions")
        self.model_context = avalon.get("model_context")
        self.current_datetime = avalon.get("current_datetime")

        self._timeout = timeout
        self._progress_content: list[str] = []

    @classmethod
    def from_stdin(cls, *, timeout: float = 60 * 60) -> "AvalonWorkflowClient":
        envelope = json.load(sys.stdin)
        if not isinstance(envelope, dict):
            raise ValueError("Workflow stdin must contain a JSON object.")
        return cls(envelope, timeout=timeout)

    def log(self, message: str) -> None:
        print(f"[workflow] {message}", file=sys.stderr, flush=True)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.bearer_token}"}

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, object],
    ) -> Any:
        async with httpx2.AsyncClient(
            headers=self._headers(),
            timeout=self._timeout,
        ) as http:
            transport = streamable_http_client(
                f"{self.backend_url}/mcp",
                http_client=http,
            )
            async with Client(transport) as client:
                result = await client.call_tool(name, arguments)

        return self._tool_result(result)

    async def llm(
        self,
        prompt: str,
        *,
        use_context: bool = False,
    ) -> str:
        messages: list[dict[str, str]] = []

        self._append_system(messages, self.model_persona)
        self._append_system(messages, self.model_instructions)

        if use_context:
            self._append_context(messages)

        self._append_system(messages, self.current_datetime)
        messages.append({"role": "user", "content": prompt})

        async with httpx2.AsyncClient(
            headers=self._headers(),
            timeout=self._timeout,
        ) as http:
            response = await http.post(
                f"{self.backend_url}/api/v1/llm/text",
                json={"messages": messages},
            )
            response.raise_for_status()
            body = response.json()

        content = body.get("content")
        if not isinstance(content, str) or not content:
            raise RuntimeError("Avalon LLM returned no text content.")
        return content

    async def progress(self, message: str) -> None:
        if not message:
            raise ValueError("Progress message must not be empty.")

        self._progress_content.append(message)

        async with httpx2.AsyncClient(
            headers=self._headers(),
            timeout=self._timeout,
        ) as http:
            response = await http.patch(
                f"{self.backend_url}/api/v1/workflow-executions/"
                f"{self.workflow_execution_id}/runtime",
                json={"progress_content": self._progress_content},
            )
            response.raise_for_status()

    @staticmethod
    def _append_system(
        messages: list[dict[str, str]],
        value: object,
    ) -> None:
        if isinstance(value, str) and value:
            messages.append({"role": "system", "content": value})
            return

        if isinstance(value, list):
            content = "\n".join(
                item for item in value if isinstance(item, str) and item
            )
            if content:
                messages.append({"role": "system", "content": content})

    def _append_context(self, messages: list[dict[str, str]]) -> None:
        context = self.model_context
        if not isinstance(context, list):
            return

        for message in context:
            if not isinstance(message, dict):
                continue
            role = message.get("role")
            content = message.get("content")
            if role in {"system", "user", "assistant"} and isinstance(content, str) and content:
                messages.append({"role": role, "content": content})

    @staticmethod
    def _tool_result(result: object) -> Any:
        structured = getattr(result, "structured_content", None)
        if structured is not None:
            return structured

        for item in getattr(result, "content", []):
            text = getattr(item, "text", None)
            if not isinstance(text, str):
                continue
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text

        return None
