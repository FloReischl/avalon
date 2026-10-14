"""Content analysis for collected Gmail threads without retaining mail data."""

from __future__ import annotations

import base64
import io
import json
import logging
import subprocess
import tempfile
import zipfile
from collections.abc import AsyncIterable, Callable, Iterable, Mapping
from pathlib import Path
from typing import Protocol
from xml.etree import ElementTree

from .inbox_thread_collector import CollectedThread, MailHeader


logger = logging.getLogger(__name__)

# Mirrors the existing 8,000-token compression threshold and its conservative
# three-characters-per-token estimate.  This is a character budget, not a new
# tokenizer or context-management layer.
DEFAULT_INPUT_BUDGET_CHARS = 8_000 * 3
_LLM_ATTEMPTS = 2
_WORDPROCESSING_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class ThreadAnalysisClient(Protocol):
    """The narrow workflow-client surface needed for AP3."""

    async def get_mail(self, message_id: str, *, as_text: bool = True) -> dict[str, object]: ...

    async def get_mail_attachment(
        self, message_id: str, attachment_id: str
    ) -> dict[str, str]: ...

    async def llm(self, prompt: str, **kwargs: object) -> str: ...


class InboxThreadAnalyzer:
    """Analyze one collected thread at a time and return compact proposals only."""

    def __init__(
        self,
        client: ThreadAnalysisClient,
        *,
        input_budget_chars: int = DEFAULT_INPUT_BUDGET_CHARS,
        pdf_text_extractor: Callable[[bytes], str] | None = None,
    ) -> None:
        if input_budget_chars < 1:
            raise ValueError("input_budget_chars must be positive.")
        self._client = client
        self._input_budget_chars = input_budget_chars
        self._pdf_text_extractor = pdf_text_extractor or _extract_pdf_text

    async def analyze(self, threads: AsyncIterable[CollectedThread]) -> dict[str, list[str]]:
        """Analyze sequentially; the returned mapping retains no mail content."""
        proposals: dict[str, list[str]] = {}
        async for thread in threads:
            categories = await self.analyze_thread(thread)
            if categories is not None:
                proposals[thread.thread_id] = categories
        return proposals

    async def analyze_thread(self, thread: CollectedThread) -> list[str] | None:
        """Return categories for one thread, or ``None`` when it must be skipped."""
        try:
            headers = tuple(
                sorted(thread.headers, key=lambda header: header.internal_date)
            )
            if not headers:
                raise ValueError("Collected thread has no headers.")

            evidence, has_attachments = await self._load_evidence(headers)
            technical = [f"Jahr/{max(header.internal_date for header in headers).year}"]
            if has_attachments:
                technical.append("has-attachments")
            categories = await self._suggest_categories(evidence)
            return _deduplicate([*technical, *(categories or ["Nicht kategorisiert"])])
        except Exception:
            logger.exception("Skipping thread %s during content analysis.", thread.thread_id)
            return None

    async def _load_evidence(self, headers: tuple[MailHeader, ...]) -> tuple[str, bool]:
        remaining = self._input_budget_chars
        pieces: list[str] = []
        has_attachments = False

        for header in headers:
            mail = await self._client.get_mail(header.message_id)
            if not isinstance(mail, Mapping):
                raise ValueError("Mail capability returned an invalid mail.")
            body = mail.get("body_content")
            subject = mail.get("subject")
            if not isinstance(body, str) or not isinstance(subject, str):
                raise ValueError("Mail capability returned unreadable message content.")

            remaining = _append_budgeted(
                pieces,
                remaining,
                f"Nachricht {header.internal_date.isoformat()}\nBetreff: {subject}\n{body}\n",
            )
            attachments = mail.get("attachments")
            if not isinstance(attachments, list):
                raise ValueError("Mail capability returned invalid attachments.")
            has_attachments = has_attachments or bool(attachments)

            for attachment in attachments:
                if remaining <= 0:
                    break
                if not isinstance(attachment, Mapping):
                    continue
                attachment_text = await self._attachment_text(header.message_id, attachment)
                if attachment_text:
                    name = attachment.get("name")
                    label = name if isinstance(name, str) and name else "Anhang"
                    remaining = _append_budgeted(
                        pieces, remaining, f"Anhang {label}:\n{attachment_text}\n"
                    )
        return "".join(pieces), has_attachments

    async def _attachment_text(
        self, message_id: str, attachment: Mapping[str, object]
    ) -> str:
        name = attachment.get("name")
        attachment_id = attachment.get("id")
        mime_type = attachment.get("mime_type")
        if not isinstance(name, str) or not isinstance(attachment_id, str):
            return ""
        kind = _supported_attachment_kind(name, mime_type)
        if kind is None:
            return ""
        try:
            result = await self._client.get_mail_attachment(message_id, attachment_id)
            encoded = result.get("content_base64") if isinstance(result, Mapping) else None
            if not isinstance(encoded, str):
                raise ValueError("Attachment capability returned no Base64 content.")
            content = base64.b64decode(encoded, validate=True)
            if kind == "pdf":
                return self._pdf_text_extractor(content)
            if kind == "docx":
                return _extract_docx_text(content)
            return _extract_doc_text(content, name)
        except Exception:
            logger.exception("Skipping unreadable attachment %s on mail %s.", name, message_id)
            return ""

    async def _suggest_categories(self, evidence: str) -> list[str] | None:
        prompt = _category_prompt(evidence, self._input_budget_chars)
        invalid_response = False
        for attempt in range(_LLM_ATTEMPTS):
            try:
                response = await self._client.llm(
                    prompt,
                    persona=None,
                    context=None,
                    instructions=(
                        "Antworte ausschließlich mit dem verlangten JSON. "
                        "Keine technischen Kategorien und keine Begründungen."
                    ),
                )
            except Exception:
                logger.exception("LLM failed while analyzing a mail thread.")
                raise
            categories = _parse_categories(response)
            if categories is not None:
                return categories
            invalid_response = True
            logger.warning(
                "LLM returned invalid category JSON (attempt %d/%d).",
                attempt + 1,
                _LLM_ATTEMPTS,
            )
        if invalid_response:
            raise ValueError("LLM returned invalid category JSON repeatedly.")
        return None


def _append_budgeted(pieces: list[str], remaining: int, value: str) -> int:
    if remaining <= 0 or not value:
        return remaining
    clipped = value[:remaining]
    pieces.append(clipped)
    return remaining - len(clipped)


def _supported_attachment_kind(name: str, mime_type: object) -> str | None:
    suffix = Path(name).suffix.lower()
    normalized_mime = mime_type.lower() if isinstance(mime_type, str) else ""
    if suffix == ".pdf" or normalized_mime == "application/pdf":
        return "pdf"
    if suffix == ".docx" or normalized_mime == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        return "docx"
    if suffix == ".doc" or normalized_mime == "application/msword":
        return "doc"
    return None


def _extract_pdf_text(content: bytes) -> str:
    """Use the already installed local pdftotext utility; never OCR."""
    with tempfile.TemporaryDirectory(prefix="avalon-mail-pdf-") as directory:
        source = Path(directory) / "attachment.pdf"
        source.write_bytes(content)
        result = subprocess.run(
            ["pdftotext", str(source), "-"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    return result.stdout if result.returncode == 0 else ""


def _extract_docx_text(content: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            document = archive.read("word/document.xml")
        root = ElementTree.fromstring(document)
    except (KeyError, OSError, ValueError, zipfile.BadZipFile, ElementTree.ParseError):
        return ""
    paragraphs = []
    for paragraph in root.iter(f"{_WORDPROCESSING_NS}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{_WORDPROCESSING_NS}t"))
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def _extract_doc_text(content: bytes, name: str) -> str:
    """Extract legacy .doc only when the installed LibreOffice can convert it."""
    with tempfile.TemporaryDirectory(prefix="avalon-mail-doc-") as directory:
        source = Path(directory) / (Path(name).name or "attachment.doc")
        source.write_bytes(content)
        result = subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to",
                "txt:Text",
                "--outdir",
                directory,
                str(source),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        target = source.with_suffix(".txt")
        if result.returncode != 0 or not target.is_file():
            return ""
        return target.read_text(encoding="utf-8", errors="replace")


def _category_prompt(evidence: str, budget: int) -> str:
    prefix = (
        "Ordne diesem E-Mail-Thread wenige aussagekräftige fachliche Kategorien zu. "
        "Nutze keine technischen Kategorien, keine Erklärungen und keine überfeine Taxonomie. "
        "Antworte ausschließlich als JSON-Objekt im Format {\"categories\":[\"Bereich/Typ\"]}.\n\n"
        "Thread-Inhalte:\n"
    )
    return (prefix + evidence)[:budget]


def _parse_categories(response: object) -> list[str] | None:
    if not isinstance(response, str):
        return None
    try:
        payload = json.loads(response)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or set(payload) != {"categories"}:
        return None
    values = payload["categories"]
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        return None
    return _deduplicate(
        value.strip()
        for value in values
        if value.strip() and not _is_technical_category(value.strip())
    )


def _is_technical_category(value: str) -> bool:
    return value == "has-attachments" or (
        value.startswith("Jahr/") and value[5:].isdigit() and len(value) == 9
    )


def _deduplicate(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
