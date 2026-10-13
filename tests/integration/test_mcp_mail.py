
"""Manueller Integrationstest gegen den laufenden Avalon-MCP-Server."""

import asyncio
import json
import os

import pytest
import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from app.config import settings
from app.mcp.security import bearer_token_for_agent

MCP_URL = f"http://127.0.0.1:8095/mcp"
MESSAGE_ID = "1878841908482608973"

pytestmark = pytest.mark.integration


def test_get_mail_body_over_real_mcp_backend():
    if os.getenv("AVALON_RUN_MAIL_MCP_TEST") != "1":
        pytest.skip("Set AVALON_RUN_MAIL_MCP_TEST=1 to enable")

    async def run():
        bearer_token = bearer_token_for_agent(agent_id=1)

        headers = {"Authorization": f"Bearer {bearer_token}"}
        async with httpx2.AsyncClient(headers=headers) as http:
            transport = streamable_http_client(MCP_URL, http_client=http)
            async with Client(transport) as client:
                provider_result = await client.call_tool(
                    "mail.set_provider",
                    {"provider": "gmail"},
                )
                assert not provider_result.is_error, provider_result

                mail_result = await client.call_tool(
                    "mail.get_mail",
                    {"message_id": MESSAGE_ID},
                )
                assert not mail_result.is_error, mail_result

            print("\n=== RAW MCP RESPONSE ===")
            print(
                json.dumps(
                    mail_result.model_dump(mode="json", exclude_none=True),
                    ensure_ascii=False,
                    indent=2,
                )
            )

            print("\n=== MAIL BODY ===")
            structured = getattr(mail_result, "structured_content", None)

            if isinstance(structured, dict):
                mail = structured
            else:
                # MCP text result may contain serialized JSON.
                text = "\n".join(
                    block.text
                    for block in mail_result.content
                    if getattr(block, "type", None) == "text"
                )
                mail = json.loads(text)

            print(f"\n--- Body: {mail['body_mime_type']} ---")
            print(mail["body_content"])

            assert mail["message_id"] == MESSAGE_ID
            assert "body" not in mail

    asyncio.run(run())



if __name__ == "__main__":
    os.environ["AVALON_RUN_MAIL_MCP_TEST"] = "1"
    pytest.main([__file__, "-v", "-s", "--capture=no"])
