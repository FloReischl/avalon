import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import create_app


def post_chat(message: str):
    async def request_chat():
        transport = ASGITransport(app=create_app())
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/api/v1/chat", json={"message": message})

    return asyncio.run(request_chat())


def test_chat_endpoint_explicitly_reports_stub() -> None:
    response = post_chat("Hallo")

    assert response.status_code == 501
    assert response.json() == {
        "detail": "Text chat is not implemented yet.",
    }


def test_chat_rejects_empty_message() -> None:
    response = post_chat("")

    assert response.status_code == 422
