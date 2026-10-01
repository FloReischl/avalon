"""Local bearer transport for Avalon principal identification.

The unsigned JWT-shaped payload identifies a principal only within the local
Linux-user boundary.  It is deliberately not authentication for external use.
"""

import base64
import json
from contextvars import ContextVar

from fastapi import HTTPException


current_principal_id: ContextVar[int | None] = ContextVar("principal_id", default=None)


def bearer_token_for_principal(principal_id: int) -> str:
    """Create the provisional unsigned bearer token for one principal."""
    if not isinstance(principal_id, int) or isinstance(principal_id, bool) or principal_id < 1:
        raise ValueError("principal_id must be a positive integer.")

    def encode(value: dict[str, object]) -> str:
        return base64.urlsafe_b64encode(
            json.dumps(value, separators=(",", ":")).encode()
        ).decode().rstrip("=")

    return f"{encode({'alg': 'none', 'typ': 'JWT'})}.{encode({'principal_id': principal_id})}."


def principal_from_authorization(value: str | None) -> int:
    if not value or not value.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required.")
    try:
        parts = value.removeprefix("Bearer ").split(".")
        if len(parts) != 3 or not parts[0] or not parts[1]:
            raise ValueError("Malformed token")
        payload = parts[1]
        payload += "=" * (-len(payload) % 4)
        principal_id = json.loads(base64.urlsafe_b64decode(payload))["principal_id"]
    except (KeyError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid bearer token.") from exc
    if not isinstance(principal_id, int) or isinstance(principal_id, bool) or principal_id < 1:
        raise HTTPException(status_code=401, detail="Invalid bearer token.")
    return principal_id
