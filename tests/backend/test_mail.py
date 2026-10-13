import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.mail.gmail import GmailMailProvider
from app.mail.manager import MailProviderManager
from app.mail.models import MailMessage, MailProviderStats
from app.mail.providers import NoActiveMailProviderError, UnsupportedMailProviderError
from app.mcp.mail import register_mail_tools
from mcp.server import MCPServer


class FakeProvider:
    def __init__(self, fail=False):
        self.connect_calls = 0
        self.fail = fail

    def connect(self):
        self.connect_calls += 1
        if self.fail:
            raise RuntimeError("offline")

    def disconnect(self): pass
    def get_provider_stats(self): return MailProviderStats(0, 0, 0, None, None)
    def get_messages(self, *_): return []
    def get_messages_by_thread(self, *_): return []


def test_provider_selection_is_atomic_and_repeat_is_noop():
    state = SimpleNamespace(active_mail_provider=None)
    gmail, broken = FakeProvider(), FakeProvider(fail=True)
    manager = MailProviderManager(lambda: state, {"gmail": lambda: gmail, "broken": lambda: broken})

    manager.set_provider("gmail")
    manager.set_provider("gmail")
    with pytest.raises(RuntimeError, match="offline"):
        manager.set_provider("broken")

    assert gmail.connect_calls == 1
    assert state.active_mail_provider == "gmail"


def test_provider_manager_requires_active_and_rejects_unknown():
    state = SimpleNamespace(active_mail_provider=None)
    manager = MailProviderManager(lambda: state, {})
    with pytest.raises(NoActiveMailProviderError):
        manager.get_provider_stats()
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
    def fetch(self, identifier, _):
        self.calls.append(("fetch", identifier))
        if identifier in (b"1", b"*") and _ == "(INTERNALDATE)":
            return "OK", [(b'1 (INTERNALDATE "01-Jan-2026 12:00:00 +0000")', b"")]
        suffix = b"\\Seen" if identifier == b"1" else b""
        metadata = b'1 (X-GM-MSGID 99 X-GM-THRID 77 FLAGS (' + suffix + b') INTERNALDATE "01-Jan-2026 12:00:00 +0000")'
        return "OK", [(metadata, b"From: Alice <alice@example.test>\r\nSubject: Hallo\r\n\r\n")]
    def logout(self): return "BYE", []


def test_gmail_reads_metadata_filters_precisely_and_finds_archived_thread(tmp_path, monkeypatch):
    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    fake = FakeImap()
    provider = GmailMailProvider(config, imap_factory=lambda *_: fake, sleep=lambda _: None)
    credentials = SimpleNamespace(token="token", to_json=lambda: "{}")
    monkeypatch.setattr(provider, "_credentials", lambda: credentials)
    provider.connect()

    messages = provider.get_messages("INBOX", datetime(2026, 1, 1, 12, tzinfo=timezone.utc), datetime(2026, 1, 2, tzinfo=timezone.utc))
    thread = provider.get_messages_by_thread("77")

    assert [(m.message_id, m.thread_id, m.subject, m.sender, m.is_read) for m in messages] == [("99", "77", "Hallo", "Alice <alice@example.test>", True), ("99", "77", "Hallo", "Alice <alice@example.test>", False)]
    assert len(thread) == 2
    assert ("select", '"[Gmail]/Alle Nachrichten"') in fake.calls


def test_gmail_stats_uses_special_use_all_mail_and_empty_mailbox(tmp_path, monkeypatch):
    config = SimpleNamespace(account="a@example.test", oauth_token=tmp_path / "token.json", client_secret=tmp_path / "client.json")
    fake = FakeImap()
    provider = GmailMailProvider(config, imap_factory=lambda *_: fake, sleep=lambda _: None)
    monkeypatch.setattr(provider, "_credentials", lambda: SimpleNamespace(token="token", to_json=lambda: "{}"))
    provider.connect()
    stats = provider.get_provider_stats()
    assert stats == MailProviderStats(2, 2, 1, datetime(2026, 1, 1, 12, tzinfo=timezone.utc), datetime(2026, 1, 1, 12, tzinfo=timezone.utc))


def test_mail_mcp_validates_dates_before_provider_access():
    state = SimpleNamespace(active_mail_provider=None)
    manager = MailProviderManager(lambda: state, {})
    mcp = MCPServer("Test")
    register_mail_tools(mcp, manager)
    with pytest.raises(Exception):
        asyncio.run(mcp.call_tool("mail.get_messages", {"category": "INBOX", "since": "2026-01-02T00:00:00", "before": "2026-01-01T00:00:00"}))
