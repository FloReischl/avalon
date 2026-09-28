"""Application service for fetching LLM-ready web content."""

from urllib.parse import urljoin, urlparse

import httpx
import trafilatura


class WebContentService:
    """Fetch HTML or plaintext resources with validated redirects."""

    _TIMEOUT_SECONDS = 10
    _MAX_REDIRECTS = 20
    _MAX_CONTENT_CHARS = 20_000
    _SUPPORTED_CONTENT_TYPES = {"text/html", "text/plain"}
    _REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}

    async def get_content(self, url: str) -> dict[str, str | bool]:
        """Fetch, extract, and bound content, propagating fetch/extraction errors."""
        self._validate_url(url)
        async with httpx.AsyncClient(
            timeout=self._TIMEOUT_SECONDS,
            follow_redirects=False,
        ) as client:
            response = await self._get_final_response(client, url)

        content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        if content_type not in self._SUPPORTED_CONTENT_TYPES:
            raise ValueError(f"Unsupported content type: {content_type or 'missing'}")

        content = self._extract_content(response, content_type)
        truncated = len(content) > self._MAX_CONTENT_CHARS
        return {
            "url": str(response.url),
            "content": content[: self._MAX_CONTENT_CHARS],
            "truncated": truncated,
        }

    async def _get_final_response(
        self, client: httpx.AsyncClient, url: str
    ) -> httpx.Response:
        current_url = url
        for _ in range(self._MAX_REDIRECTS + 1):
            response = await client.get(current_url)
            if response.status_code not in self._REDIRECT_STATUS_CODES:
                response.raise_for_status()
                return response

            location = response.headers.get("location")
            if location is None:
                response.raise_for_status()
                raise ValueError("Redirect response has no Location header")
            current_url = urljoin(str(response.url), location)
            self._validate_url(current_url)
        raise httpx.TooManyRedirects("Exceeded maximum redirects")

    @staticmethod
    def _validate_url(url: str) -> None:
        if urlparse(url).scheme not in {"http", "https"}:
            raise ValueError("Only http and https URLs are supported")

    @staticmethod
    def _extract_content(response: httpx.Response, content_type: str) -> str:
        if content_type == "text/plain":
            return response.text
        content = trafilatura.extract(response.text, output_format="markdown")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Could not extract main content from HTML")
        return content
