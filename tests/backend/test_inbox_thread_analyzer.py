"""Offline contracts for Gmail inbox-organizer AP3 thread analysis."""

import asyncio
import base64
import io
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "workflows"))

from avalon_workflows.inbox_thread_analyzer import InboxThreadAnalyzer
from avalon_workflows.inbox_thread_collector import CollectedThread, MailHeader


def header(message_id: str, when: str) -> MailHeader:
    return MailHeader(message_id, "thread-1", datetime.fromisoformat(when).replace(tzinfo=timezone.utc), "ignored", "sender", True)


def attachment(name: str, attachment_id: str, mime_type: str) -> dict[str, str]:
    return {"name": name, "id": attachment_id, "mime_type": mime_type}


def docx(text: str) -> bytes:
    document = f'''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>'''
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("word/document.xml", document)
    return output.getvalue()


class FakeClient:
    def __init__(self, mails: dict[str, object], attachments: dict[tuple[str, str], object], llm_results: list[object]) -> None:
        self.mails = mails
        self.attachments = attachments
        self.llm_results = llm_results
        self.llm_prompts: list[str] = []

    async def get_mail(self, message_id: str, *, as_text: bool = True) -> dict[str, object]:
        result = self.mails[message_id]
        if isinstance(result, Exception):
            raise result
        return result  # type: ignore[return-value]

    async def get_mail_attachment(self, message_id: str, attachment_id: str) -> dict[str, str]:
        result = self.attachments[(message_id, attachment_id)]
        if isinstance(result, Exception):
            raise result
        return result  # type: ignore[return-value]

    async def llm(self, prompt: str, **_kwargs: object) -> str:
        self.llm_prompts.append(prompt)
        result = self.llm_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result  # type: ignore[return-value]


async def items(*threads: CollectedThread):
    for thread in threads:
        yield thread


def test_analyzes_complete_thread_chronologically_with_technical_and_document_categories() -> None:
    pdf = base64.b64encode(b"PDF bytes").decode()
    word = base64.b64encode(docx("Vertrag Versicherung")).decode()
    client = FakeClient(
        {
            "new": {"subject": "Neu", "body_content": "zweiter Text", "attachments": [attachment("contract.docx", "word", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")]},
            "old": {"subject": "Alt", "body_content": "erster Text", "attachments": [attachment("invoice.pdf", "pdf", "application/pdf")]},
        },
        {("old", "pdf"): {"content_base64": pdf}, ("new", "word"): {"content_base64": word}},
        [json.dumps({"categories": ["Finanzen/Rechnungen", "Finanzen/Rechnungen"]})],
    )
    analyzer = InboxThreadAnalyzer(client, pdf_text_extractor=lambda _: "Rechnung 42")
    thread = CollectedThread("thread-1", (header("new", "2025-02-01T10:00:00"), header("old", "2024-12-31T10:00:00")))

    result = asyncio.run(analyzer.analyze(items(thread)))

    assert result == {"thread-1": ["Jahr/2025", "has-attachments", "Finanzen/Rechnungen"]}
    prompt = client.llm_prompts[0]
    assert prompt.index("erster Text") < prompt.index("zweiter Text")
    assert "Rechnung 42" in prompt and "Vertrag Versicherung" in prompt


def test_budget_limits_mail_and_attachment_content_and_skips_unsupported_files() -> None:
    client = FakeClient(
        {"one": {"subject": "S", "body_content": "x" * 500, "attachments": [attachment("scan.png", "image", "image/png"), attachment("notes.txt", "text", "text/plain")] }},
        {},
        [json.dumps({"categories": []})],
    )
    analyzer = InboxThreadAnalyzer(client, input_budget_chars=200)
    thread = CollectedThread("thread-1", (header("one", "2025-01-01T00:00:00"),))

    assert asyncio.run(analyzer.analyze(items(thread))) == {"thread-1": ["Jahr/2025", "has-attachments", "Nicht kategorisiert"]}
    assert len(client.llm_prompts[0]) <= 200


def test_invalid_llm_output_retries_then_skips_but_empty_valid_list_falls_back() -> None:
    thread = CollectedThread("thread-1", (header("one", "2025-01-01T00:00:00"),))
    mail = {"one": {"subject": "S", "body_content": "Body", "attachments": []}}
    invalid = FakeClient(mail, {}, ["not json", "[]"])
    fallback = FakeClient(mail, {}, [json.dumps({"categories": ["Jahr/2025", "has-attachments"]})])

    assert asyncio.run(InboxThreadAnalyzer(invalid).analyze(items(thread))) == {}
    assert len(invalid.llm_prompts) == 2
    assert asyncio.run(InboxThreadAnalyzer(fallback).analyze(items(thread))) == {"thread-1": ["Jahr/2025", "Nicht kategorisiert"]}


def test_scanned_pdf_and_llm_technical_failure_are_not_misclassified_as_uncategorized() -> None:
    thread = CollectedThread("thread-1", (header("one", "2025-01-01T00:00:00"),))
    client = FakeClient(
        {"one": {"subject": "S", "body_content": "Body", "attachments": [attachment("scan.pdf", "scan", "application/pdf")]}},
        {("one", "scan"): {"content_base64": base64.b64encode(b"not OCR text").decode()}},
        [RuntimeError("LLM unavailable")],
    )

    assert asyncio.run(
        InboxThreadAnalyzer(client, pdf_text_extractor=lambda _: "").analyze(items(thread))
    ) == {}


def test_unreadable_attachment_is_skipped_without_losing_the_thread() -> None:
    thread = CollectedThread("thread-1", (header("one", "2025-01-01T00:00:00"),))
    client = FakeClient(
        {"one": {"subject": "S", "body_content": "Body", "attachments": [attachment("broken.pdf", "broken", "application/pdf"), attachment("good.docx", "good", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")] }},
        {("one", "broken"): RuntimeError("download failed"), ("one", "good"): {"content_base64": base64.b64encode(docx("Reisebuchung")).decode()}},
        [json.dumps({"categories": ["Reisen/Buchungen"]})],
    )

    assert asyncio.run(InboxThreadAnalyzer(client).analyze(items(thread))) == {
        "thread-1": ["Jahr/2025", "has-attachments", "Reisen/Buchungen"]
    }
    assert "Reisebuchung" in client.llm_prompts[0]


def test_unreadable_message_or_llm_failure_skips_only_that_thread_and_keeps_no_content_state() -> None:
    bad = CollectedThread("bad", (MailHeader("bad", "bad", datetime(2025, 1, 1, tzinfo=timezone.utc), "", "", True),))
    good = CollectedThread("good", (MailHeader("good", "good", datetime(2025, 1, 2, tzinfo=timezone.utc), "", "", True),))
    client = FakeClient(
        {"bad": RuntimeError("unreadable"), "good": {"subject": "S", "body_content": "B", "attachments": []}},
        {},
        [json.dumps({"categories": ["Reisen/Buchungen"]})],
    )
    analyzer = InboxThreadAnalyzer(client)

    assert asyncio.run(analyzer.analyze(items(bad, good))) == {"good": ["Jahr/2025", "Reisen/Buchungen"]}
    assert not any("body" in name or "attachment" in name for name in analyzer.__dict__)
