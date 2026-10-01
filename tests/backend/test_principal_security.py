"""Contracts for local bearer-based principal identification."""

import asyncio

import pytest
from fastapi import Depends, FastAPI, HTTPException, Request
from httpx import ASGITransport, AsyncClient

from app.main import PrincipalBearerMiddleware, require_api_principal
from app.mcp.security import (
    bearer_token_for_principal,
    current_principal_id,
    principal_from_authorization,
)


def test_principal_token_round_trip() -> None:
    token = bearer_token_for_principal(42)

    assert principal_from_authorization(f"Bearer {token}") == 42


@pytest.mark.parametrize(
    "authorization",
    [None, "Basic value", "Bearer invalid", "Bearer eyJhbGciOiJub25lIn0.e30.", "Bearer eyJhbGciOiJub25lIn0.eyJwcmluY2lwYWxfaWQiOjB9."],
)
def test_invalid_principal_tokens_are_rejected_without_a_default(authorization: str | None) -> None:
    with pytest.raises(HTTPException) as error:
        principal_from_authorization(authorization)

    assert error.value.status_code == 401


def test_middleware_sets_principal_only_for_principal_relevant_routes() -> None:
    application = FastAPI(dependencies=[Depends(require_api_principal)])

    @application.get("/api/v1/chats")
    def chats(request: Request) -> dict[str, int | None]:
        return {"principal_id": request.scope.get("avalon.principal_id")}

    @application.get("/api/v1/ui/config")
    async def config(request: Request) -> dict[str, int | None]:
        return {"principal_id": request.scope.get("avalon.principal_id")}

    application.add_middleware(PrincipalBearerMiddleware)

    async def request(path: str, headers: dict[str, str] | None = None):
        async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
            return await client.get(path, headers=headers)

    assert asyncio.run(request("/api/v1/chats")).status_code == 401
    authorized = asyncio.run(
        request("/api/v1/chats", {"Authorization": f"Bearer {bearer_token_for_principal(7)}"})
    )
    assert authorized.json() == {"principal_id": 7}
    assert asyncio.run(request("/api/v1/ui/config")).json() == {"principal_id": None}
