"""Small client SDK for Avalon workflow scripts."""

from __future__ import annotations

import json
import sys
from typing import Any, Optional

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from .confirmation import ConfirmationTable

DEFAULT = object()



class ConfirmationCancelled(Exception):
    """The user cancelled a workflow confirmation in Avalon."""


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
        persona: Optional[str] | Any = DEFAULT,
        instructions: Optional[str] | Any = DEFAULT,
        context: Optional[str] | Any = DEFAULT,
    ) -> str:
        messages: list[dict[str, str]] = []

        # persona
        active_persona = self.model_persona if persona is DEFAULT else persona
        if active_persona:
            self._append_system(messages, active_persona)

        # instructions
        active_instructions = (
            self.model_instructions if instructions is DEFAULT else instructions
        )
        if active_instructions:
            self._append_system(messages, active_instructions)

        # context
        self._append_context(messages, context)

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

    async def confirm(
        self,
        confirmation: ConfirmationTable | dict[str, object],
    ) -> list[dict[str, object]]:
        """Wait for the user to review workflow rows in Avalon."""
        if isinstance(confirmation, ConfirmationTable):
            payload = confirmation.to_dict()
        elif isinstance(confirmation, dict):
            payload = confirmation
        else:
            raise TypeError("confirmation must be ConfirmationTable or dict.")

        async with httpx2.AsyncClient(
            headers=self._headers(),
            timeout=self._timeout,
        ) as http:
            response = await http.post(
                f"{self.backend_url}/api/v1/workflow-executions/"
                f"{self.workflow_execution_id}/confirmation",
                json=payload,
            )


        if response.status_code == 409:
            body = response.json()
            if isinstance(body, dict) and body.get("detail") == "workflow_confirmation_cancelled":
                raise ConfirmationCancelled

        response.raise_for_status()
        result = response.json()
        if not isinstance(result, list):
            raise RuntimeError("Avalon confirmation returned invalid rows.")
        return result

    def payload_as_list(self) -> list[Any]:
        payload = self.payload

        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "Workflow payload string must contain valid JSON."
                ) from exc

        if isinstance(payload, dict) and len(payload) == 1:
            payload = next(iter(payload.values()))

        if isinstance(payload, list):
            return payload

        raise ValueError(
            "Workflow payload must be a list or contain exactly one list value."
        )

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

    def _append_context(self, messages: list[dict[str, str]], active_context: Optional[list] | Any = DEFAULT) -> None:
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
