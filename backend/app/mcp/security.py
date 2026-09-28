"""Temporary MCP bearer-token boundary.

This parses only the provisional unsigned internal token.  It must be replaced
by real JWT signature and claim validation before external principals exist.
"""

import base64
import json
from contextvars import ContextVar

from fastapi import HTTPException


current_principal_id: ContextVar[int | None] = ContextVar("mcp_principal_id", default=None)


def principal_from_authorization(value: str | None) -> int:
    if not value or not value.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="MCP requires a bearer token.")
    try:
        payload = value.removeprefix("Bearer ").split(".")[1]
        payload += "=" * (-len(payload) % 4)
        principal_id = json.loads(base64.urlsafe_b64decode(payload))["principal_id"]
    except (IndexError, KeyError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid MCP bearer token.") from exc
    if not isinstance(principal_id, int) or principal_id < 1:
        raise HTTPException(status_code=401, detail="Invalid MCP bearer token.")
    return principal_id
