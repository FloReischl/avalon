import asyncio

import httpx
import pytest

from app.services.web_content import WebContentService


def test_html_is_extracted_as_markdown(httpx_mock):
    httpx_mock.add_response(
        url="https://example.test/article",
        headers={"content-type": "text/html; charset=utf-8"},
        text="<html><body><main><h1>Avalon</h1><p>Local AI companion.</p></main></body></html>",
    )

    result = asyncio.run(WebContentService().get_content("https://example.test/article"))

    assert result == {
        "url": "https://example.test/article",
        "content": "Avalon\nLocal AI companion.",
        "truncated": False,
    }


def test_plaintext_is_returned_unchanged(httpx_mock):
    httpx_mock.add_response(
        url="https://example.test/readme.txt",
        headers={"content-type": "text/plain"},
        text="Avalon\nLocal AI",
    )

    assert asyncio.run(WebContentService().get_content("https://example.test/readme.txt")) == {
        "url": "https://example.test/readme.txt",
        "content": "Avalon\nLocal AI",
        "truncated": False,
    }


def test_content_is_limited_to_twenty_thousand_characters(httpx_mock):
    httpx_mock.add_response(
        url="https://example.test/long.txt",
        headers={"content-type": "text/plain"},
        text="x" * 20_001,
    )

    result = asyncio.run(WebContentService().get_content("https://example.test/long.txt"))

    assert result["content"] == "x" * 20_000
    assert result["truncated"] is True


def test_invalid_initial_scheme_is_rejected_without_request():
    with pytest.raises(ValueError, match="Only http and https"):
        asyncio.run(WebContentService().get_content("file:///etc/passwd"))


def test_http_redirect_is_followed(httpx_mock):
    httpx_mock.add_response(
        url="https://example.test/redirect",
        status_code=302,
        headers={"location": "/article.txt"},
    )
    httpx_mock.add_response(
        url="https://example.test/article.txt",
        headers={"content-type": "text/plain"},
        text="Redirected content",
    )

    assert asyncio.run(WebContentService().get_content("https://example.test/redirect")) == {
        "url": "https://example.test/article.txt",
        "content": "Redirected content",
        "truncated": False,
    }


def test_redirect_to_invalid_scheme_is_rejected(httpx_mock):
    httpx_mock.add_response(
        url="https://example.test/redirect",
        status_code=302,
        headers={"location": "file:///etc/passwd"},
    )

    with pytest.raises(ValueError, match="Only http and https"):
        asyncio.run(WebContentService().get_content("https://example.test/redirect"))


def test_non_success_status_is_propagated(httpx_mock):
    httpx_mock.add_response(url="https://example.test/missing", status_code=404)

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(WebContentService().get_content("https://example.test/missing"))


def test_unsupported_content_type_is_rejected(httpx_mock):
    httpx_mock.add_response(
        url="https://example.test/image.png",
        headers={"content-type": "image/png"},
        content=b"png",
    )

    with pytest.raises(ValueError, match="Unsupported content type"):
        asyncio.run(WebContentService().get_content("https://example.test/image.png"))


def test_timeout_is_propagated(httpx_mock):
    httpx_mock.add_exception(httpx.ReadTimeout("timed out"), url="https://example.test/slow")

    with pytest.raises(httpx.ReadTimeout, match="timed out"):
        asyncio.run(WebContentService().get_content("https://example.test/slow"))
