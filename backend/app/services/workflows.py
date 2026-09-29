"""Out-of-process execution of registered workflows."""

from __future__ import annotations

import asyncio
import json
import logging
import sys

from pydantic import JsonValue

from app.workflows_config import WorkflowsConfig, get_workflows_config


logger = logging.getLogger(__name__)


class WorkflowExecutionError(RuntimeError):
    """A registered workflow ended unsuccessfully."""


class WorkflowService:
    """Resolve server-owned workflow keys and execute them safely."""

    def __init__(self, config: WorkflowsConfig | None = None) -> None:
        self._config = config

    async def execute(self, workflow_key: str, payload: JsonValue) -> None:
        config = self._config or get_workflows_config()
        try:
            workflow = config.get(workflow_key)
        except KeyError as exc:
            raise WorkflowExecutionError(f"Unknown workflow: {workflow_key}") from exc

        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(workflow.file_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        )
        if process.returncode != 0:
            logger.error(
                "workflow=%s exit_code=%s stdout=%r stderr=%r",
                workflow_key,
                process.returncode,
                stdout.decode("utf-8", errors="replace"),
                stderr.decode("utf-8", errors="replace"),
            )
            raise WorkflowExecutionError(
                f"Workflow {workflow_key!r} exited with code {process.returncode}."
            )
