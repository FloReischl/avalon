"""Preferred mail-body selection and safe HTML-to-text conversion."""

from __future__ import annotations

import re
from collections.abc import Iterable

import html2text


_HTML_DOCUMENT_MARKER = re.compile(r"<!doctype\s+html|<(?:html|head|body)\b", re.IGNORECASE)
_HTML_STRUCTURE_TAG = re.compile(r"<(?:article|div|footer|h[1-6]|header|li|main|ol|p|section|table|td|tr|ul)\b[^>]*>", re.IGNORECASE)


def select_preferred_body(parts: Iterable[tuple[str, str]]) -> tuple[str, str]:
    """Prefer HTML, then plaintext, and otherwise return an empty plaintext body."""
    parts = list(parts)
    return next(
        (part for part in parts if part[0] == "text/html"),
        next((part for part in parts if part[0] == "text/plain"), ("text/plain", "")),
    )


def looks_like_html(content: str) -> bool:
    """Recognize document-like HTML without treating isolated tags as HTML."""
    if _HTML_DOCUMENT_MARKER.search(content):
        return True
    return len(_HTML_STRUCTURE_TAG.findall(content)) >= 2


def render_body(mime_type: str, content: str, as_text: bool) -> tuple[str, str]:
    """Return the requested representation without losing content on conversion errors."""
    is_html = mime_type == "text/html" or (mime_type == "text/plain" and looks_like_html(content))
    if not as_text:
        return ("text/html" if is_html else mime_type, content)
    if not is_html:
        return "text/plain", content
    try:
        converter = html2text.HTML2Text()
        converter.body_width = 0
        return "text/plain", converter.handle(content)
    except Exception:
        return "text/plain", content
