import asyncio
import pytest

from app.services.web_search import WebSearchService


def test_default_provider_uses_duckduckgo_with_required_settings(monkeypatch):
    calls: dict[str, object] = {}

    class FakeDDGS:
        def __init__(self, *, timeout: int) -> None:
            calls["timeout"] = timeout

        def text(self, query: str, **kwargs: object) -> list[dict[str, str]]:
            calls["query"] = query
            calls.update(kwargs)
            return []

    monkeypatch.setattr("app.services.web_search.DDGS", FakeDDGS)

    assert asyncio.run(WebSearchService().search("Avalon")) == []
    assert calls == {
        "timeout": 10,
        "query": "Avalon",
        "region": "de-de",
        "safesearch": "off",
        "max_results": 5,
        "backend": "duckduckgo",
    }


def test_search_maps_provider_result():
    service = WebSearchService(
        lambda _: [
            {
                "title": "Avalon",
                "href": "https://example.test/avalon",
                "body": "Local AI companion",
            }
        ]
    )

    assert asyncio.run(service.search("Avalon local AI")) == [
        {
            "title": "Avalon",
            "url": "https://example.test/avalon",
            "snippet": "Local AI companion",
        }
    ]


def test_search_limits_results_and_allows_empty_results():
    provider_results = [
        {"title": str(index), "href": f"https://example.test/{index}", "body": "x"}
        for index in range(6)
    ]

    assert len(asyncio.run(WebSearchService(lambda _: provider_results).search("Avalon"))) == 5
    assert asyncio.run(WebSearchService(lambda _: []).search("Avalon")) == []


def test_search_propagates_error_without_retry():
    calls = 0

    def broken_provider(_: str) -> list[dict[str, str]]:
        nonlocal calls
        calls += 1
        raise ConnectionError("provider unavailable")

    with pytest.raises(ConnectionError, match="provider unavailable"):
        asyncio.run(WebSearchService(broken_provider).search("Avalon"))
    assert calls == 1


def test_search_uses_ten_second_timeout(monkeypatch):
    observed_timeout: float | None = None

    async def timeout_immediately(awaitable, *, timeout):
        nonlocal observed_timeout
        observed_timeout = timeout
        await awaitable
        raise asyncio.TimeoutError

    monkeypatch.setattr("app.services.web_search.asyncio.wait_for", timeout_immediately)
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(WebSearchService(lambda _: []).search("Avalon"))
    assert observed_timeout == 10


def test_search_rejects_invalid_provider_response():
    with pytest.raises(ValueError, match="invalid result"):
        asyncio.run(WebSearchService(lambda _: [{"title": "Avalon"}]).search("Avalon"))
