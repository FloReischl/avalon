import asyncio
import os
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.mail.gmail import GmailMailProvider
import app.mail.gmail as gmail_module
from app.mail.manager import MailProviderManager
from app.mail.models import MailMessage, MailProviderStats
from app.mail.providers import MailAuthenticationError, MailProtocolError, NoActiveMailProviderError, UnsupportedMailProviderError
from app.mcp.mail import register_mail_tools
import app.mcp.mail as mcp_mail_module
from mcp.server import MCPServer
from app.authorization.guard import PermissionGuard
from app.authorization.permissions import build_permission_registry
from app.authorization.requests import AuthorizationRequestManager


class FakeProvider:
    def __init__(self, fail=False, fail_disconnect=False):
        self.connect_calls = 0
        self.disconnect_calls = 0
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
