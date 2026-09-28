import asyncio
from contextlib import asynccontextmanager

import app.mcp.client as client_module
from app.mcp.client import HttpMcpToolClient


def test_mcp_requests_allow_one_hour_for_authorization(monkeypatch):
    observed: dict[str, object] = {}

    class FakeHttpClient:
        def __init__(self, **kwargs):
            observed.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

    @asynccontextmanager
    async def fake_transport(*_, **__):
        yield object()

    class FakeMcpClient:
        def __init__(self, _):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

    monkeypatch.setattr(client_module.httpx2, "AsyncClient", FakeHttpClient)
    monkeypatch.setattr(client_module, "streamable_http_client", fake_transport)
    monkeypatch.setattr(client_module, "Client", FakeMcpClient)

    assert asyncio.run(HttpMcpToolClient(2)._request(lambda _: _result())) == "done"
    assert observed["timeout"] == 3600


async def _result() -> str:
    return "done"
