"""Application service for DuckDuckGo web search."""

import asyncio
from collections.abc import Callable, Mapping
from typing import Any

from ddgs import DDGS


SearchProvider = Callable[[str], list[dict[str, Any]]]


class WebSearchService:
    """Search DuckDuckGo without blocking the application event loop."""

    _TIMEOUT_SECONDS = 10
    _MAX_RESULTS = 5

    def __init__(self, provider: SearchProvider | None = None) -> None:
        self._provider = provider or self._search_duckduckgo

    async def search(self, query: str) -> list[dict[str, str]]:
        """Return up to five normalized search results or propagate the failure."""
        raw_results = await asyncio.wait_for(
            asyncio.to_thread(self._provider, query),
            timeout=self._TIMEOUT_SECONDS,
        )
        if not isinstance(raw_results, list):
            raise ValueError("DuckDuckGo provider returned an invalid response")

        return [self._map_result(result) for result in raw_results[: self._MAX_RESULTS]]

    @classmethod
    def _search_duckduckgo(cls, query: str) -> list[dict[str, Any]]:
        return DDGS(timeout=cls._TIMEOUT_SECONDS).text(
            query,
            region="de-de",
            safesearch="off",
            max_results=cls._MAX_RESULTS,
            backend="duckduckgo",
        )

    @staticmethod
    def _map_result(result: object) -> dict[str, str]:
        if not isinstance(result, Mapping):
            raise ValueError("DuckDuckGo provider returned an invalid result")

        title = result.get("title")
        url = result.get("href")
        snippet = result.get("body")
        if not all(isinstance(value, str) for value in (title, url, snippet)):
            raise ValueError("DuckDuckGo provider returned an invalid result")

        return {"title": title, "url": url, "snippet": snippet}
