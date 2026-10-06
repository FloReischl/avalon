"""Local bearer transport for Avalon agent identification.

The unsigned JWT-shaped payload identifies an agent only within the local
Linux-user boundary.  It is deliberately not authentication for external use.
"""

import base64
import json
from contextvars import ContextVar

from fastapi import HTTPException


current_agent_id: ContextVar[int | None] = ContextVar("agent_id", default=None)


def bearer_token_for_agent(agent_id: int) -> str:
    """Create the provisional unsigned bearer token for one agent."""
    if not isinstance(agent_id, int) or isinstance(agent_id, bool) or agent_id < 1:
        raise ValueError("agent_id must be a positive integer.")

    def encode(value: dict[str, object]) -> str:
        return base64.urlsafe_b64encode(
            json.dumps(value, separators=(",", ":")).encode()
        ).decode().rstrip("=")

    return f"{encode({'alg': 'none', 'typ': 'JWT'})}.{encode({'agent_id': agent_id})}."


def agent_from_authorization(value: str | None) -> int:
    if not value or not value.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required.")
    try:
        parts = value.removeprefix("Bearer ").split(".")
        if len(parts) != 3 or not parts[0] or not parts[1]:
            raise ValueError("Malformed token")
        payload = parts[1]
        payload += "=" * (-len(payload) % 4)
        agent_id = json.loads(base64.urlsafe_b64decode(payload))["agent_id"]
    except (KeyError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid bearer token.") from exc
    if not isinstance(agent_id, int) or isinstance(agent_id, bool) or agent_id < 1:
        raise HTTPException(status_code=401, detail="Invalid bearer token.")
    return agent_id
