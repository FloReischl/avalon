import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import create_app


def test_health_reports_ready_backend() -> None:
    async def request_health():
        transport = ASGITransport(app=create_app())
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Avalon Backend",
    }
