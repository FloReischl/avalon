"""Contracts for local bearer-based agent identification."""

import asyncio

import pytest
from fastapi import Depends, FastAPI, HTTPException, Request
from httpx import ASGITransport, AsyncClient

from app.main import AgentBearerMiddleware, require_api_agent
from app.mcp.security import (
    bearer_token_for_agent,
    current_agent_id,
    agent_from_authorization,
)


def test_agent_token_round_trip() -> None:
    token = bearer_token_for_agent(42)

    assert agent_from_authorization(f"Bearer {token}") == 42


@pytest.mark.parametrize(
    "authorization",
    [None, "Basic value", "Bearer invalid", "Bearer eyJhbGciOiJub25lIn0.e30.", "Bearer eyJhbGciOiJub25lIn0.eyJwcmluY2lwYWxfaWQiOjB9."],
)
def test_invalid_agent_tokens_are_rejected_without_a_default(authorization: str | None) -> None:
    with pytest.raises(HTTPException) as error:
        agent_from_authorization(authorization)

    assert error.value.status_code == 401


def test_middleware_sets_agent_only_for_agent_relevant_routes() -> None:
    application = FastAPI(dependencies=[Depends(require_api_agent)])

    @application.get("/api/v1/chats")
    def chats(request: Request) -> dict[str, int | None]:
        return {"agent_id": request.scope.get("avalon.agent_id")}

    @application.get("/api/v1/ui/config")
    async def config(request: Request) -> dict[str, int | None]:
        return {"agent_id": request.scope.get("avalon.agent_id")}

    application.add_middleware(AgentBearerMiddleware)

    async def requests():
        async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
            unauthorized = await client.get("/api/v1/chats")
            authorized = await client.get(
                "/api/v1/chats",
                headers={"Authorization": f"Bearer {bearer_token_for_agent(7)}"},
            )
            config = await client.get("/api/v1/ui/config")
        return unauthorized, authorized, config

    unauthorized, authorized, config = asyncio.run(requests())
    assert unauthorized.status_code == 401
    assert authorized.json() == {"agent_id": 7}
    assert config.json() == {"agent_id": None}
