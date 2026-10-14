import asyncio
import os
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.mail.gmail import GmailMailProvider
import app.mail.gmail as gmail_module
from app.mail.body import looks_like_html, render_body, select_preferred_body
from app.mail.manager import MailProviderManager
from app.mail.models import Mail, MailAttachmentContent, MailMessage, MailProviderStats, MailSender
from app.mail.providers import MailAuthenticationError, MailProtocolError, NoActiveMailProviderError, UnsupportedMailProviderError
from app.mcp.mail import register_mail_tools
import app.mcp.mail as mcp_mail_module
from app.mcp.server import AuthorizedMcpServer
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from app.authorization.guard import PermissionGuard
from app.authorization.permissions import build_permission_registry
from app.authorization.requests import AuthorizationRequestManager


class FakeProvider:
    def __init__(self, fail=False, fail_disconnect=False):
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.cache_invalidations = 0
        self.fail = fail
        self.fail_disconnect = fail_disconnect

    def connect(self):
        self.connect_calls += 1
        if self.fail:
            raise RuntimeError("offline")

    def disconnect(self):
        self.disconnect_calls += 1
        if self.fail_disconnect:
            raise RuntimeError("disconnect failed")
    def get_provider_stats(self): return MailProviderStats(0, 0, 0, None, None)
    def get_messages(self, *_): return []
    def get_messages_by_thread(self, *_): return []
    def get_mail(self, *_): return None
    def get_attachment(self, *_): return MailAttachmentContent("", "application/octet-stream", b"")
    def get_categories(self): return []
    def create_categories(self, *_): return None
    def set_categories(self, *_): return None
    def unset_categories(self, *_): return None
    def invalidate_categories_cache(self): self.cache_invalidations += 1


def test_provider_selection_is_atomic_and_repeat_is_noop():
    state = SimpleNamespace(active_mail_provider=None)
    gmail, broken = FakeProvider(), FakeProvider(fail=True)
    manager = MailProviderManager(lambda: state, {"gmail": lambda: gmail, "broken": lambda: broken})

    manager.set_provider("gmail")
    manager.set_provider("gmail")
    with pytest.raises(RuntimeError, match="offline"):
        manager.set_provider("broken")

    assert gmail.connect_calls == 1
    assert gmail.cache_invalidations == 2
    assert state.active_mail_provider == "gmail"


def test_provider_switch_disconnects_previous_only_after_new_connection():
    state = SimpleNamespace(active_mail_provider=None)
    gmail, other = FakeProvider(), FakeProvider()
    manager = MailProviderManager(lambda: state, {"gmail": lambda: gmail, "other": lambda: other})
    manager.set_provider("gmail")
    manager.set_provider("other")
    assert gmail.disconnect_calls == 1
    assert state.active_mail_provider == "other"


def test_provider_switch_remains_successful_when_old_disconnect_fails(caplog):
    state = SimpleNamespace(active_mail_provider=None)
    gmail, other = FakeProvider(fail_disconnect=True), FakeProvider()
    manager = MailProviderManager(lambda: state, {"gmail": lambda: gmail, "other": lambda: other})
    manager.set_provider("gmail")
    manager.set_provider("other")
    assert state.active_mail_provider == "other"
    assert other.connect_calls == 1
    assert "Could not disconnect inactive mail provider 'gmail'" in caplog.text


def test_provider_manager_requires_active_and_rejects_unknown():
    state = SimpleNamespace(active_mail_provider=None)
    manager = MailProviderManager(lambda: state, {})
    with pytest.raises(NoActiveMailProviderError):
        manager.get_provider_stats()
    with pytest.raises(NoActiveMailProviderError):
        manager.get_mail("99")
    with pytest.raises(NoActiveMailProviderError):
        manager.get_attachment("99", "2")
    with pytest.raises(NoActiveMailProviderError):
        manager.get_categories()
    with pytest.raises(UnsupportedMailProviderError):
        manager.set_provider("mailbox")


class FakeImap:
    def __init__(self, *_): self.calls = []
    def authenticate(self, *_): self.calls.append("authenticate"); return "OK", []
    def list(self): self.calls.append("list"); return "OK", [b'(\\All) "/" "[Gmail]/Alle Nachrichten"']
    def select(self, mailbox, readonly):
        self.calls.append(("select", mailbox)); return "OK", [b"2"]
    def search(self, _, *criteria):
        self.calls.append(("search", criteria)); return "OK", [b"1 2"] if criteria != ("UNSEEN",) else [b"2"]
    def fetch(self, identifier, query):
        self.calls.append(("fetch", identifier))
        date = b"01-Jan-2026 12:00:00 +0000" if identifier == b"1" else b"01-Jan-2026 12:00:01 +0000"
        if identifier in (b"1", b"*") and query == "(INTERNALDATE)":
            return "OK", [(b'1 (INTERNALDATE "' + date + b'")', b"")]
        suffix = b"\\Seen" if identifier == b"1" else b""
        message_id = b"99" if identifier == b"1" else b"100"
        metadata = b'1 (X-GM-MSGID ' + message_id + b' X-GM-THRID 77 FLAGS (' + suffix + b') INTERNALDATE "' + date + b'")'
        return "OK", [(metadata, b"From: Alice <alice@example.test>\r\nSubject: Hallo\r\n\r\n")]
    def logout(self): return "BYE", []


def test_gmail_reads_metadata_filters_precisely_and_finds_archived_thread(tmp_path, monkeypatch):
    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    fake = FakeImap()
    provider = GmailMailProvider(config, imap_factory=lambda *_: fake, sleep=lambda _: None)
    credentials = SimpleNamespace(token="token", to_json=lambda: "{}")
    monkeypatch.setattr(provider, "_credentials", lambda: credentials)
    provider.connect()

    messages = provider.get_messages("INBOX", datetime(2026, 1, 1, 12, tzinfo=timezone.utc), datetime(2026, 1, 1, 12, 0, 1, tzinfo=timezone.utc))
    thread = provider.get_messages_by_thread("77")

    assert [(m.message_id, m.thread_id, m.subject, m.sender, m.is_read) for m in messages] == [("99", "77", "Hallo", "Alice <alice@example.test>", True)]
    assert [message.message_id for message in thread] == ["99", "100"]
    assert ("select", '"[Gmail]/Alle Nachrichten"') in fake.calls


def test_gmail_get_mail_prefers_html_and_preserves_attachment_metadata(tmp_path, monkeypatch):
    class DetailImap(FakeImap):
        def fetch(self, identifier, query):
            self.calls.append(("fetch", identifier, query))
            metadata = (
                b'1 (X-GM-MSGID 99 X-GM-THRID 77 FLAGS () '
                b'INTERNALDATE "01-Jan-2026 12:00:00 +0000")'
            )
            raw_message = (
                b"From: Alice Example <alice@example.test>\r\n"
                b"Subject: =?utf-8?q?Gr=C3=BC=C3=9Fe?=\r\n"
                b"Content-Type: multipart/mixed; boundary=outer\r\n\r\n"
                b"--outer\r\nContent-Type: multipart/alternative; boundary=inner\r\n\r\n"
                b"--inner\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nHallo\r\n"
                b"--inner\r\nContent-Type: text/html; charset=utf-8\r\n\r\n<p>Hallo</p>\r\n"
                b"--inner--\r\n"
                b"--outer\r\nContent-Type: application/pdf\r\n"
                b"Content-Disposition: attachment; filename=invoice.pdf\r\n"
                b"Content-Transfer-Encoding: base64\r\n\r\ncGRm\r\n"
                b"--outer\r\nContent-Type: image/png\r\n"
                b"Content-Disposition: attachment; filename=image.png\r\n"
                b"Content-Transfer-Encoding: base64\r\n\rcG5n\r\n"
                b"--outer--\r\n"
            )
            return "OK", [(metadata, raw_message)]

        def search(self, _, *criteria):
            self.calls.append(("search", criteria))
            return "OK", [b"1"] if criteria == ("X-GM-MSGID", "99") else super().search(_, *criteria)

    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    fake = DetailImap()
    provider = GmailMailProvider(config, imap_factory=lambda *_: fake, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()

    mail = provider.get_mail("99")
    original_mail = provider.get_mail("99", as_text=False)

    assert mail.message_id == "99"
    assert mail.is_read is False
    assert mail.internal_date == datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    assert mail.subject == "Grüße"
    assert (mail.sender.name, mail.sender.email_address) == ("Alice Example", "alice@example.test")
    assert mail.thread_id == "77"
    assert (mail.body_mime_type, mail.body_content) == ("text/plain", "Hallo\n")
    assert (original_mail.body_mime_type, original_mail.body_content) == ("text/html", "<p>Hallo</p>")
    assert [(attachment.name, attachment.id, attachment.mime_type) for attachment in mail.attachments] == [
        ("invoice.pdf", "4", "application/pdf"),
        ("image.png", "5", "image/png"),
    ]
    assert len({attachment.id for attachment in mail.attachments}) == len(mail.attachments)
    assert ("select", '"[Gmail]/Alle Nachrichten"') in fake.calls
    assert any(
        call == ("fetch", b"1", "(X-GM-MSGID X-GM-THRID FLAGS INTERNALDATE BODY.PEEK[])")
        for call in fake.calls
    )


def test_gmail_get_attachment_uses_get_mail_attachment_ids_and_preserves_bytes(tmp_path, monkeypatch):
    class AttachmentImap(FakeImap):
        def search(self, _, *criteria):
            return "OK", [b"1"] if criteria == ("X-GM-MSGID", "99") else [b""]

        def fetch(self, identifier, query):
            metadata = b'1 (X-GM-MSGID 99 FLAGS () INTERNALDATE "01-Jan-2026 12:00:00 +0000")'
            raw_message = (
                b"Content-Type: multipart/mixed; boundary=outer\r\n\r\n"
                b"--outer\r\nContent-Type: text/plain\r\n\r\nBody\r\n"
                b"--outer\r\nContent-Type: application/octet-stream\r\n"
                b"Content-Disposition: attachment; filename=bytes.bin\r\n"
                b"Content-Transfer-Encoding: base64\r\n\r\nAP+AQUIA/w==\r\n"
                b"--outer--\r\n"
            )
            return "OK", [(metadata, raw_message)]

    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    provider = GmailMailProvider(config, imap_factory=AttachmentImap, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()

    mail = provider.get_mail("99")
    attachment = provider.get_attachment("99", mail.attachments[0].id)

    assert [(item.name, item.id, item.mime_type) for item in mail.attachments] == [
        ("bytes.bin", "2", "application/octet-stream"),
    ]
    assert attachment == MailAttachmentContent("bytes.bin", "application/octet-stream", b"\x00\xff\x80AB\x00\xff")


def test_gmail_get_mail_excludes_text_attachments_from_the_body(tmp_path, monkeypatch):
    class AttachmentImap(FakeImap):
        def search(self, _, *criteria): return "OK", [b"1"]

        def fetch(self, identifier, query):
            metadata = b'1 (X-GM-MSGID 99 FLAGS () INTERNALDATE "01-Jan-2026 12:00:00 +0000")'
            raw_message = (
                b"Content-Type: multipart/mixed; boundary=outer\r\n\r\n"
                b"--outer\r\nContent-Type: text/plain\r\n\r\nMail body\r\n"
                b"--outer\r\nContent-Type: text/plain\r\n"
                b"Content-Disposition: attachment; filename=notes.txt\r\n\r\nAttachment body\r\n"
                b"--outer--\r\n"
            )
            return "OK", [(metadata, raw_message)]

    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    provider = GmailMailProvider(config, imap_factory=AttachmentImap, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()

    mail = provider.get_mail("99")

    assert (mail.body_mime_type, mail.body_content) == ("text/plain", "Mail body")
    assert [(item.name, item.mime_type) for item in mail.attachments] == [("notes.txt", "text/plain")]


def test_gmail_get_attachment_resolves_all_ids_in_nested_mime_parts(tmp_path, monkeypatch):
    class AttachmentImap(FakeImap):
        def search(self, _, *criteria): return "OK", [b"1"]

        def fetch(self, identifier, query):
            metadata = b'1 (X-GM-MSGID 99 FLAGS () INTERNALDATE "01-Jan-2026 12:00:00 +0000")'
            raw_message = (
                b"Content-Type: multipart/mixed; boundary=outer\r\n\r\n"
                b"--outer\r\nContent-Type: multipart/alternative; boundary=inner\r\n\r\n"
                b"--inner\r\nContent-Type: text/plain\r\n\r\nBody\r\n--inner--\r\n"
                b"--outer\r\nContent-Type: application/pdf\r\nContent-Disposition: attachment; filename=one.pdf\r\n\r\none\r\n"
                b"--outer\r\nContent-Type: multipart/mixed; boundary=nested\r\n\r\n"
                b"--nested\r\nContent-Type: image/png\r\nContent-Disposition: attachment; filename=two.png\r\n\r\ntwo\r\n"
                b"--nested--\r\n--outer--\r\n"
            )
            return "OK", [(metadata, raw_message)]

    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    provider = GmailMailProvider(config, imap_factory=AttachmentImap, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()

    mail = provider.get_mail("99")

    assert [(item.id, item.name) for item in mail.attachments] == [("3", "one.pdf"), ("5", "two.png")]
    assert [provider.get_attachment("99", item.id).content for item in mail.attachments] == [b"one", b"two"]


def test_gmail_get_attachment_reconstructs_attached_rfc822_bytes(tmp_path, monkeypatch):
    class AttachmentImap(FakeImap):
        def search(self, _, *criteria): return "OK", [b"1"]

        def fetch(self, identifier, query):
            metadata = b'1 (X-GM-MSGID 99 FLAGS () INTERNALDATE "01-Jan-2026 12:00:00 +0000")'
            raw_message = (
                b"Content-Type: multipart/mixed; boundary=outer\r\n\r\n"
                b"--outer\r\nContent-Type: message/rfc822\r\n"
                b"Content-Disposition: attachment; filename=forwarded.eml\r\n\r\n"
                b"From: sender@example.test\r\nSubject: Forwarded\r\n\r\nBody\r\n"
                b"--outer--\r\n"
            )
            return "OK", [(metadata, raw_message)]

    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    provider = GmailMailProvider(config, imap_factory=AttachmentImap, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()

    mail = provider.get_mail("99")
    attachment = provider.get_attachment("99", mail.attachments[0].id)

    assert (attachment.file_name, attachment.mime_type) == ("forwarded.eml", "message/rfc822")
    assert attachment.content == b"From: sender@example.test\r\nSubject: Forwarded\r\n\r\nBody"


def test_gmail_get_attachment_rejects_unknown_or_wrong_message_attachment_id(tmp_path, monkeypatch):
    class AttachmentImap(FakeImap):
        def search(self, _, *criteria):
            return "OK", [b"1"] if criteria == ("X-GM-MSGID", "99") else [b""]

        def fetch(self, identifier, query):
            metadata = b'1 (X-GM-MSGID 99 FLAGS () INTERNALDATE "01-Jan-2026 12:00:00 +0000")'
            return "OK", [(metadata, b"Content-Type: text/plain\r\n\r\nBody")]

    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    provider = GmailMailProvider(config, imap_factory=AttachmentImap, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()

    with pytest.raises(MailProtocolError, match="attachment ID"):
        provider.get_attachment("99", "2")
    with pytest.raises(MailProtocolError, match="message ID was not found"):
        provider.get_attachment("100", "2")


@pytest.mark.parametrize(
    ("raw_message", "expected_body"),
    [
        (b"Subject: Plain\r\n\r\nPlain body", ("text/plain", "Plain body")),
        (
            b"Subject: HTML\r\nContent-Type: text/html; charset=utf-8\r\n\r\n<strong>HTML</strong>",
            ("text/plain", "**HTML**\n"),
        ),
        (b"Subject: Empty\r\nContent-Type: application/octet-stream\r\n\r\n", ("text/plain", "")),
    ],
)
def test_gmail_get_mail_handles_single_or_missing_displayable_body(tmp_path, monkeypatch, raw_message, expected_body):
    class BodyImap(FakeImap):
        def search(self, _, *criteria):
            return "OK", [b"1"]

        def fetch(self, identifier, query):
            metadata = b'1 (X-GM-MSGID 99 FLAGS () INTERNALDATE "01-Jan-2026 12:00:00 +0000")'
            return "OK", [(metadata, raw_message)]

    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    provider = GmailMailProvider(config, imap_factory=BodyImap, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()

    mail = provider.get_mail("99")

    assert (mail.body_mime_type, mail.body_content) == expected_body
    assert mail.attachments == []
    assert (mail.sender.name, mail.sender.email_address, mail.thread_id) == ("", "", None)


def test_gmail_get_mail_keeps_an_attached_message_out_of_the_main_body(tmp_path, monkeypatch):
    class AttachedMessageImap(FakeImap):
        def search(self, _, *criteria):
            return "OK", [b"1"]

        def fetch(self, identifier, query):
            metadata = b'1 (X-GM-MSGID 99 FLAGS () INTERNALDATE "01-Jan-2026 12:00:00 +0000")'
            raw_message = (
                b"Content-Type: multipart/mixed; boundary=outer\r\n\r\n"
                b"--outer\r\nContent-Type: text/plain\r\n\r\nOuter body\r\n"
                b"--outer\r\nContent-Type: message/rfc822\r\n"
                b"Content-Disposition: attachment; filename=forwarded.eml\r\n\r\n"
                b"Content-Type: text/html\r\n\r\n<p>Attached body</p>\r\n"
                b"--outer--\r\n"
            )
            return "OK", [(metadata, raw_message)]

    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    provider = GmailMailProvider(config, imap_factory=AttachedMessageImap, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()

    mail = provider.get_mail("99")

    assert (mail.body_mime_type, mail.body_content) == ("text/plain", "Outer body")
    assert [(attachment.name, attachment.mime_type) for attachment in mail.attachments] == [
        ("forwarded.eml", "message/rfc822"),
    ]


def test_gmail_skips_a_malformed_displayable_mime_part():
    class BrokenPart:
        def is_multipart(self): return False
        def get_content_disposition(self): return None
        def get_filename(self): return None
        def get_content_type(self): return "text/plain"
        def get_payload(self, decode):
            assert decode is True
            raise ValueError("broken transfer encoding")

    class Root:
        def is_multipart(self): return True
        def get_content_disposition(self): return None
        def get_filename(self): return None
        def get_content_type(self): return "multipart/mixed"
        def get_payload(self): return [BrokenPart()]

    assert GmailMailProvider._content_parts(Root()) == ([], [])


def test_mail_body_selection_detection_and_rendering_are_conservative():
    assert select_preferred_body([("text/plain", "Plain"), ("text/html", "<p>HTML</p>")]) == (
        "text/html",
        "<p>HTML</p>",
    )
    assert select_preferred_body([]) == ("text/plain", "")
    assert looks_like_html("<!DOCTYPE html><html><body><p>HTML</p></body></html>")
    assert looks_like_html("<div><p>HTML</p></div>")
    assert looks_like_html("<div>Hello <strong>world</strong></div>")
    assert not looks_like_html("Use <tag> only as a placeholder.")
    assert render_body("text/plain", "Use <tag> only as a placeholder.", True) == (
        "text/plain",
        "Use <tag> only as a placeholder.",
    )


def test_mail_body_conversion_error_keeps_the_original_content(monkeypatch):
    def broken_handle(_, __):
        raise RuntimeError("converter failed")

    monkeypatch.setattr("app.mail.body.html2text.HTML2Text.handle", broken_handle)

    assert render_body("text/html", "<p>Original</p>", True) == ("text/html", "<p>Original</p>")


def test_gmail_get_mail_converts_misdeclared_html_and_can_return_original_body(tmp_path, monkeypatch):
    class HtmlImap(FakeImap):
        def search(self, _, *criteria):
            return "OK", [b"1"]

        def fetch(self, identifier, query):
            metadata = b'1 (X-GM-MSGID 99 FLAGS () INTERNALDATE "01-Jan-2026 12:00:00 +0000")'
            raw_message = (
                b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
                b"<!DOCTYPE html><html><body><p>Hello <strong>world</strong></p></body></html>"
            )
            return "OK", [(metadata, raw_message)]

    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    provider = GmailMailProvider(config, imap_factory=HtmlImap, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()

    converted = provider.get_mail("99")
    original = provider.get_mail("99", as_text=False)

    assert (converted.body_mime_type, converted.body_content) == ("text/plain", "Hello **world**\n")
    assert original.body_mime_type == "text/html"
    assert original.body_content.startswith("<!DOCTYPE html>")


def test_gmail_get_categories_returns_system_custom_and_nested_labels(tmp_path, monkeypatch):
    class CategoriesImap(FakeImap):
        def list(self):
            return "OK", [
                b'(\\HasNoChildren \\Inbox) "/" "INBOX"',
                b'(\\HasNoChildren \\All) "/" "[Gmail]/Alle Nachrichten"',
                b'(\\HasChildren) "/" "Projects"',
                b'(\\HasNoChildren) "/" "Projects/2026"',
                b'(\\HasNoChildren) "/" "&ZeVnLIqe-"',
            ]

    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    provider = GmailMailProvider(config, imap_factory=CategoriesImap, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()

    assert provider.get_categories() == ["INBOX", "[Gmail]/Alle Nachrichten", "Projects", "Projects/2026", "日本語"]


def test_gmail_rejects_malformed_mailbox_escaping_and_modified_utf7():
    with pytest.raises(MailProtocolError, match="parse Gmail mailbox"):
        GmailMailProvider._parse_mailbox_name(b'(\\HasNoChildren) "/" "broken\\q"')
    with pytest.raises(MailProtocolError, match="decode Gmail mailbox"):
        GmailMailProvider._parse_mailbox_name(b'(\\HasNoChildren) "/" "&!!!!-"')


def test_gmail_get_mail_and_categories_report_imap_failures(tmp_path, monkeypatch):
    class FailingImap(FakeImap):
        def search(self, *_): return "NO", []
        def list(self): return "NO", []

    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    provider = GmailMailProvider(config, imap_factory=FailingImap, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()

    with pytest.raises(MailProtocolError, match="labels"):
        provider.get_categories()
    with pytest.raises(MailProtocolError, match="All Mail"):
        provider.get_mail("99")


def test_gmail_get_mail_reports_fetch_failure(tmp_path, monkeypatch):
    class FetchFailingImap(FakeImap):
        def search(self, _, *criteria): return "OK", [b"1"]
        def fetch(self, *_): return "NO", []

    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    provider = GmailMailProvider(config, imap_factory=FetchFailingImap, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()

    with pytest.raises(MailProtocolError, match="requested message"):
        provider.get_mail("99")
    with pytest.raises(MailProtocolError, match="requested message"):
        provider.get_attachment("99", "2")


def test_gmail_get_mail_rejects_invalid_or_unknown_message_ids(tmp_path, monkeypatch):
    class EmptySearchImap(FakeImap):
        def search(self, *_):
            return "OK", [b""]

    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    provider = GmailMailProvider(config, imap_factory=EmptySearchImap, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()

    with pytest.raises(ValueError, match="message_id"):
        provider.get_mail("not-an-id")
    with pytest.raises(MailProtocolError, match="not found"):
        provider.get_mail("99")


def test_mail_mcp_registers_new_tools_and_delegates_to_manager():
    calls = []

    class Manager:
        def get_mail(self, message_id, as_text=True):
            calls.append(("mail", message_id, as_text))
            return Mail(
                message_id=message_id,
                is_read=True,
                internal_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                subject="",
                sender=MailSender(name="", email_address=""),
                thread_id=None,
                body_mime_type="text/plain",
                body_content="",
                attachments=[],
            )

        def get_categories(self):
            calls.append(("categories",))
            return []

        def get_attachment(self, message_id, attachment_id):
            calls.append(("attachment", message_id, attachment_id))
            return MailAttachmentContent("invoice.pdf", "application/pdf", b"\x00\xff")

        def create_categories(self, categories):
            calls.append(("create", categories))

        def set_categories(self, message_id, categories, archive=False):
            calls.append(("set", message_id, categories, archive))

        def unset_categories(self, message_id, categories):
            calls.append(("unset", message_id, categories))

    mcp = MCPServer("Test")
    register_mail_tools(mcp, Manager())

    result = asyncio.run(mcp.call_tool("mail.get_mail", {"message_id": "99", "as_text": False}))
    attachment_result = asyncio.run(mcp.call_tool("mail.get_attachment", {"message_id": "99", "attachment_id": "4"}))
    asyncio.run(mcp.call_tool("mail.get_categories", {}))
    asyncio.run(mcp.call_tool("mail.create_categories", {"categories": ["Project"]}))
    asyncio.run(mcp.call_tool("mail.set_categories", {"message_id": "99", "categories": ["Project"], "archive": True}))
    asyncio.run(mcp.call_tool("mail.unset_categories", {"message_id": "99", "categories": ["Project"]}))

    assert calls == [
        ("mail", "99", False), ("attachment", "99", "4"), ("categories",), ("create", ["Project"]),
        ("set", "99", ["Project"], True), ("unset", "99", ["Project"]),
    ]
    assert "body" not in result.structured_content
    assert result.structured_content["body_mime_type"] == "text/plain"
    assert attachment_result.structured_content == {
        "file_name": "invoice.pdf", "mime_type": "application/pdf", "content_base64": "AP8=",
    }


def test_mail_get_attachment_surfaces_provider_errors_as_mcp_tool_errors():
    class Manager:
        def get_attachment(self, message_id, attachment_id):
            raise MailProtocolError("Gmail IMAP command failed.")

    mcp = MCPServer("Test")
    register_mail_tools(mcp, Manager())

    with pytest.raises(ToolError, match="Gmail IMAP command failed"):
        asyncio.run(mcp.call_tool("mail.get_attachment", {"message_id": "99", "attachment_id": "2"}))


def test_new_mail_tools_use_the_existing_mail_read_permission():
    class Repository:
        def get_permission_catalog_id(self, context, key):
            assert (context, key) == ("mail", "read")
            return 7

    assert AuthorizedMcpServer._resolve_permission("mail.get_mail", Repository()) == ("mail", "read", 7)
    assert AuthorizedMcpServer._resolve_permission("mail.get_attachment", Repository()) == ("mail", "read", 7)
    assert AuthorizedMcpServer._resolve_permission("mail.get_categories", Repository()) == ("mail", "read", 7)


def test_mail_category_writes_use_mail_write_permission():
    class Repository:
        def get_permission_catalog_id(self, context, key):
            return {("mail", "read"): 7, ("mail", "write"): 8}.get((context, key))

    assert AuthorizedMcpServer._resolve_permission("mail.create_categories", Repository()) == ("mail", "write", 8)
    assert AuthorizedMcpServer._resolve_permission("mail.set_categories", Repository()) == ("mail", "write", 8)
    assert AuthorizedMcpServer._resolve_permission("mail.unset_categories", Repository()) == ("mail", "write", 8)


def test_gmail_category_mutations_validate_cache_and_archive_in_order(tmp_path, monkeypatch):
    class CategoriesImap(FakeImap):
        def __init__(self, *_):
            super().__init__()
            self.labels = [
                b'(\\HasNoChildren \\Inbox) "/" "INBOX"',
                b'(\\HasNoChildren \\All) "/" "[Gmail]/All Mail"',
                b'(\\HasNoChildren) "/" "Project"',
            ]
            self.stores = []
            self.creates = []

        def list(self):
            self.calls.append("list")
            return "OK", self.labels

        def create(self, name):
            self.creates.append(name)
            return "OK", []

        def store(self, identifier, operation, labels):
            self.stores.append((identifier, operation, labels))
            return "OK", []

    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    fake = CategoriesImap()
    provider = GmailMailProvider(config, imap_factory=lambda *_: fake, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()

    provider.set_categories("99", ["Project"], archive=True)
    provider.unset_categories("99", ["INBOX", "Project"])
    provider.create_categories(["Project", "New", "New"])

    assert fake.stores == [
        (b"1", "+X-GM-LABELS", '("Project")'),
        (b"1", "-X-GM-LABELS", '("INBOX")'),
        (b"1", "-X-GM-LABELS", '("INBOX" "Project")'),
    ]
    assert fake.creates == ['"New"']
    assert fake.calls.count("list") == 4  # lazy validation, two All-Mail lookups, direct create
    assert provider._category_cache is None


def test_gmail_category_mutations_fully_validate_before_writing(tmp_path, monkeypatch):
    class CategoriesImap(FakeImap):
        def __init__(self, *_):
            super().__init__()
            self.stores = []
        def list(self): return "OK", [b'(\\HasNoChildren \\Inbox) "/" "INBOX"', b'(\\HasNoChildren \\All) "/" "[Gmail]/All Mail"', b'(\\HasNoChildren) "/" "Project"']
        def store(self, *args): self.stores.append(args); return "OK", []

    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    fake = CategoriesImap()
    provider = GmailMailProvider(config, imap_factory=lambda *_: fake, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()

    with pytest.raises(ValueError, match="does not exist"):
        provider.set_categories("99", ["Project", "missing"])
    with pytest.raises(ValueError, match="INBOX"):
        provider.set_categories("99", ["INBOX"], archive=True)
    with pytest.raises(ValueError, match="system"):
        provider.unset_categories("99", ["[Gmail]/All Mail"])
    assert fake.stores == []


@pytest.mark.parametrize("attribute", [b"\\Starred", b"\\Spam"])
def test_gmail_recognizes_gmail_starred_and_spam_labels_as_system_labels(attribute):
    mailbox = b"(\\HasNoChildren " + attribute + b') "/" "System"'
    assert GmailMailProvider._is_system_mailbox(mailbox) is True


def test_gmail_empty_category_mutations_still_reject_unknown_message_id(tmp_path, monkeypatch):
    class CategoriesImap(FakeImap):
        def list(self):
            return "OK", [
                b'(\\HasNoChildren \\All) "/" "[Gmail]/All Mail"',
                b'(\\HasNoChildren) "/" "Project"',
            ]

        def search(self, _, *criteria):
            if criteria == ("X-GM-MSGID", "missing"):
                return "OK", [b""]
            return super().search(_, *criteria)

        def store(self, *_):
            pytest.fail("empty category mutations must not write")

    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    provider = GmailMailProvider(config, imap_factory=CategoriesImap, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()

    with pytest.raises(MailProtocolError, match="not found"):
        provider.set_categories("missing", [])
    with pytest.raises(MailProtocolError, match="not found"):
        provider.unset_categories("missing", [])


def test_gmail_create_empty_categories_invalidates_cache(tmp_path, monkeypatch):
    class CategoriesImap(FakeImap):
        def list(self): return "OK", []
        def create(self, *_): pytest.fail("empty category creation must not create labels")

    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    provider = GmailMailProvider(config, imap_factory=CategoriesImap, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()
    provider._category_cache = [("stale", False)]

    provider.create_categories([])

    assert provider._category_cache is None


def test_gmail_category_write_failures_do_not_compensate_and_create_always_invalidates_cache(tmp_path, monkeypatch):
    class CategoriesImap(FakeImap):
        def __init__(self, *_):
            super().__init__()
            self.stores = []
            self.create_count = 0
        def list(self): return "OK", [b'(\\HasNoChildren \\Inbox) "/" "INBOX"', b'(\\HasNoChildren \\All) "/" "[Gmail]/All Mail"', b'(\\HasNoChildren) "/" "Project"']
        def create(self, _):
            self.create_count += 1
            return ("NO", []) if self.create_count == 2 else ("OK", [])
        def store(self, *args):
            self.stores.append(args)
            return ("NO", []) if len(self.stores) == 2 else ("OK", [])

    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    fake = CategoriesImap()
    provider = GmailMailProvider(config, imap_factory=lambda *_: fake, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()
    provider._category_cache = [("stale", False)]

    with pytest.raises(MailProtocolError, match="create"):
        provider.create_categories(["One", "Two"])
    assert provider._category_cache is None

    with pytest.raises(MailProtocolError, match="update"):
        provider.set_categories("99", ["Project"], archive=True)
    assert [store[1] for store in fake.stores] == ["+X-GM-LABELS", "-X-GM-LABELS"]


def test_gmail_stats_uses_special_use_all_mail_and_empty_mailbox(tmp_path, monkeypatch):
    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    fake = FakeImap()
    provider = GmailMailProvider(config, imap_factory=lambda *_: fake, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()
    stats = provider.get_provider_stats()
    assert stats == MailProviderStats(2, 2, 1, datetime(2026, 1, 1, 12, tzinfo=timezone.utc), datetime(2026, 1, 1, 12, 0, 1, tzinfo=timezone.utc))


def test_mail_mcp_validates_dates_before_provider_access():
    state = SimpleNamespace(active_mail_provider=None)
    manager = MailProviderManager(lambda: state, {})
    mcp = MCPServer("Test")
    register_mail_tools(mcp, manager)
    with pytest.raises(Exception):
        asyncio.run(mcp.call_tool("mail.get_messages", {"category": "INBOX", "since": "2026-01-02T00:00:00", "before": "2026-01-01T00:00:00"}))


def test_gmail_accepts_naive_time_and_rejects_missing_flags(tmp_path, monkeypatch):
    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    fake = FakeImap()
    provider = GmailMailProvider(config, imap_factory=lambda *_: fake, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()
    assert provider._utc_timestamp(datetime(2026, 1, 1)).tzinfo == timezone.utc
    fake.fetch = lambda *_: ("OK", [(b'1 (X-GM-MSGID 1 X-GM-THRID 1 INTERNALDATE "01-Jan-2026 12:00:00 +0000")', b"\r\n")])
    with pytest.raises(MailProtocolError, match="FLAGS"):
        provider._message(b"1", None, None)


def test_get_messages_interprets_naive_values_locally_and_defaults_before(monkeypatch):
    fixed_local_now = datetime(2026, 7, 1, 10, 0, tzinfo=timezone(timedelta(hours=2)))
    monkeypatch.setattr(mcp_mail_module, "_current_local_time", lambda: fixed_local_now)
    calls = []

    class Manager:
        def get_messages(self, category, since, before):
            calls.append((category, since, before))
            return []

    mcp = MCPServer("Test")
    register_mail_tools(mcp, Manager())
    asyncio.run(mcp.call_tool("mail.get_messages", {"category": "INBOX", "since": "2026-07-01T09:00:00+02:00"}))
    asyncio.run(mcp.call_tool("mail.get_messages", {"category": "INBOX", "since": "2026-07-01T10:00:00+03:00", "before": "2026-07-01T03:00:00-05:00"}))
    asyncio.run(mcp.call_tool("mail.get_messages", {"category": "INBOX", "before": None}))

    assert calls == [
        ("INBOX", datetime(2026, 7, 1, 7, tzinfo=timezone.utc), datetime(2026, 7, 1, 8, tzinfo=timezone.utc)),
        ("INBOX", datetime(2026, 7, 1, 7, tzinfo=timezone.utc), datetime(2026, 7, 1, 8, tzinfo=timezone.utc)),
        ("INBOX", None, datetime(2026, 7, 1, 8, tzinfo=timezone.utc)),
    ]


def test_naive_dates_use_system_timezone_with_dst_for_mcp_and_gmail():
    previous_tz = os.environ.get("TZ")
    os.environ["TZ"] = "Europe/Berlin"
    time.tzset()
    try:
        january = datetime(2026, 1, 15, 10, 0)
        july = datetime(2026, 7, 15, 10, 0)
        assert mcp_mail_module._utc_timestamp(january) == datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc)
        assert mcp_mail_module._utc_timestamp(july) == datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc)
        assert GmailMailProvider._utc_timestamp(january) == datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc)
        assert GmailMailProvider._utc_timestamp(july) == datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc)
    finally:
        if previous_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previous_tz
        time.tzset()


def test_gmail_closes_client_when_authentication_is_rejected(tmp_path, monkeypatch):
    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    fake = FakeImap()
    fake.authenticate = lambda *_: ("NO", [])
    closed = []
    fake.logout = lambda: closed.append(True) or ("BYE", [])
    provider = GmailMailProvider(config, imap_factory=lambda *_: fake)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    with pytest.raises(MailAuthenticationError):
        provider.connect()
    assert closed == [True]


def test_gmail_throttles_all_imap_commands_by_half_a_second(tmp_path):
    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    moments = iter([0.0, 0.1, 0.6])
    delays = []
    provider = GmailMailProvider(config, clock=lambda: next(moments), sleep=delays.append)
    assert provider._command(lambda: "first") == "first"
    assert provider._command(lambda: "second") == "second"
    assert delays == [pytest.approx(0.4)]


def test_gmail_stats_handles_empty_mailbox(tmp_path, monkeypatch):
    class EmptyImap(FakeImap):
        def select(self, mailbox, readonly): return "OK", [b"0"]
        def search(self, *_): return "OK", [b""]
    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    provider = GmailMailProvider(config, imap_factory=EmptyImap, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()
    assert provider.get_provider_stats() == MailProviderStats(0, 0, 0, None, None)


def test_gmail_converts_imap_command_failures_to_protocol_errors(tmp_path, monkeypatch):
    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    fake = FakeImap()
    fake.search = lambda *_: ("NO", [])
    provider = GmailMailProvider(config, imap_factory=lambda *_: fake, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()
    with pytest.raises(MailProtocolError, match="search"):
        provider.get_messages("INBOX", None, None)


def test_gmail_oauth_loads_refreshes_or_starts_browser_flow(tmp_path, monkeypatch):
    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    calls = []

    class Credentials:
        def __init__(self, valid, expired=False, refresh_token="refresh"):
            self.valid, self.expired, self.refresh_token, self.token = valid, expired, refresh_token, "access"
        def refresh(self, _): calls.append("refresh"); self.expired, self.valid = False, True
        def to_json(self): return '{"token":"access"}'
        @classmethod
        def from_authorized_user_file(cls, path, scopes):
            calls.append(("load", path, scopes)); return cls(True)

    monkeypatch.setattr(gmail_module, "Credentials", Credentials)
    config.oauth_token.write_text('{"token":"old"}', encoding="utf-8")
    assert GmailMailProvider(config)._credentials().token == "access"
    assert calls[0][0] == "load"

    refreshed = Credentials(True, expired=True)
    monkeypatch.setattr(Credentials, "from_authorized_user_file", classmethod(lambda cls, *_: refreshed))
    GmailMailProvider(config)._credentials()
    assert "refresh" in calls

    config.oauth_token.unlink()
    browser = Credentials(True)
    flow = SimpleNamespace(run_local_server=lambda **kwargs: calls.append(("browser", kwargs)) or browser)
    monkeypatch.setattr(gmail_module.InstalledAppFlow, "from_client_secrets_file", lambda *args: flow)
    GmailMailProvider(config)._credentials()
    assert any(call[0] == "browser" for call in calls if isinstance(call, tuple))
    assert config.oauth_token.stat().st_mode & 0o777 == 0o600


def test_mail_read_uses_real_permission_guard_with_existing_grant():
    now = datetime(2026, 1, 1)
    permission_set = SimpleNamespace(id=1, scope='["read"]', validity_type="permanent")
    grant = SimpleNamespace(valid_from=datetime(2025, 1, 1), valid_to=datetime(9999, 1, 1), range=None)

    class Repository:
        def get_permission_set(self, agent_id, context, key):
            assert (agent_id, context, key) == (7, "mail", "read")
            return permission_set
        def get_grants(self, permission_set_id):
            assert permission_set_id == 1
            return [grant]

    calls = []
    async def capability(items):
        calls.append(items)
        return "allowed"

    result = asyncio.run(PermissionGuard(Repository(), build_permission_registry(), AuthorizationRequestManager(), clock=lambda: now).execute(7, "mail", "read", ["read"], capability))
    assert result == "allowed"
    assert calls == [["read"]]
