"""Generate the checked-in FastAPI and MCP API documentation."""

import json
from pathlib import Path
from typing import Any

import pytest

from app.main import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[2]
API_DOCS_DIR = PROJECT_ROOT / "docs" / "api"
HTTP_METHODS = ("get", "post", "put", "patch", "delete", "options", "head")


def _json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def _render_fastapi_markdown(openapi: dict[str, Any]) -> str:
    lines = [
        "# FastAPI API",
        "",
        "> Generated from the FastAPI OpenAPI contract. Do not edit manually.",
        "",
        f"API: {openapi['info']['title']}",
        f"OpenAPI: {openapi['openapi']}",
        "",
        "The complete machine-readable contract is available in `openapi.json`.",
        "",
        "## Endpoints",
        "",
    ]

    for path in sorted(openapi.get("paths", {})):
        path_item = openapi["paths"][path]
        for method in HTTP_METHODS:
            operation = path_item.get(method)
            if operation is None:
                continue

            lines.extend(
                [
                    f"### `{method.upper()} {path}`",
                    "",
                ]
            )

            summary = operation.get("summary")
            description = operation.get("description")
            operation_id = operation.get("operationId")

            if summary:
                lines.extend([summary, ""])
            if description and description != summary:
                lines.extend([description, ""])
            if operation_id:
                lines.extend([f"Operation ID: `{operation_id}`", ""])

            parameters = operation.get("parameters")
            if parameters:
                lines.extend(
                    [
                        "**Parameters**",
                        "",
                        "```json",
                        _json(parameters),
                        "```",
                        "",
                    ]
                )

            request_body = operation.get("requestBody")
            if request_body:
                lines.extend(
                    [
                        "**Request body**",
                        "",
                        "```json",
                        _json(request_body),
                        "```",
                        "",
                    ]
                )

            responses = operation.get("responses", {})
            if responses:
                lines.extend(
                    [
                        "**Responses**",
                        "",
                        "```json",
                        _json(responses),
                        "```",
                        "",
                    ]
                )

    return "\n".join(lines).rstrip() + "\n"


def _render_mcp_markdown(tools: list[dict[str, Any]]) -> str:
    lines = [
        "# MCP Tools",
        "",
        "> Generated from the registered MCP tools. Do not edit manually.",
        "",
        "## Tools",
        "",
    ]

    for tool in sorted(tools, key=lambda item: item["name"]):
        lines.extend(
            [
                f"### `{tool['name']}`",
                "",
            ]
        )

        description = tool.get("description")
        if description:
            lines.extend([description, ""])

        input_schema = tool.get("inputSchema", {})
        lines.extend(
            [
                "**Input schema**",
                "",
                "```json",
                _json(input_schema),
                "```",
                "",
            ]
        )

        output_schema = tool.get("outputSchema")
        if output_schema is not None:
            lines.extend(
                [
                    "**Output schema**",
                    "",
                    "```json",
                    _json(output_schema),
                    "```",
                    "",
                ]
            )

    return "\n".join(lines).rstrip() + "\n"


@pytest.mark.asyncio
async def test_generate_api_documentation() -> None:
    application = create_app()

    try:
        openapi = application.openapi()
        assert openapi.get("paths"), "FastAPI OpenAPI contract contains no paths."

        mcp_tools = await application.state.mcp.list_tools()
        assert mcp_tools, "MCP server exposes no tools."

        serialized_tools = [
            tool.model_dump(by_alias=True, exclude_none=True)
            for tool in mcp_tools
        ]

        API_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        (API_DOCS_DIR / "openapi.json").write_text(
            _json(openapi) + "\n",
            encoding="utf-8",
        )
        (API_DOCS_DIR / "fastapi.md").write_text(
            _render_fastapi_markdown(openapi),
            encoding="utf-8",
        )
        (API_DOCS_DIR / "mcp.md").write_text(
            _render_mcp_markdown(serialized_tools),
            encoding="utf-8",
        )

        assert (API_DOCS_DIR / "openapi.json").stat().st_size > 0
        assert (API_DOCS_DIR / "fastapi.md").stat().st_size > 0
        assert (API_DOCS_DIR / "mcp.md").stat().st_size > 0
    finally:
        application.state.workflow_engine.dispose()