"""Gmail's IMAP/XOAUTH2 implementation of the mail provider contract."""

from __future__ import annotations

import imaplib
import os
import re
import time
from datetime import datetime, timezone
from email import message_from_bytes
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Callable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from app.mail.models import MailMessage, MailProviderStats
from app.mail.providers import MailAuthenticationError, MailConnectionError, MailProtocolError
from app.user_config import GoogleMailUserConfig


_SCOPE = "https://mail.google.com/"
_INTERNALDATE = re.compile(rb'INTERNALDATE "([^"]+)"')
_MESSAGE_ID = re.compile(rb"X-GM-MSGID (\d+)")
_THREAD_ID = re.compile(rb"X-GM-THRID (\d+)")
_FLAGS = re.compile(rb"FLAGS \(([^)]*)\)")
_MAILBOX = re.compile(rb' "([^"]+)"$')


class GmailMailProvider:
    """Read metadata from Gmail without exposing bodies or attachments."""

    def __init__(
        self,
        config: GoogleMailUserConfig,
        imap_factory: Callable[..., imaplib.IMAP4_SSL] = imaplib.IMAP4_SSL,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._config = config
        self._imap_factory = imap_factory
        self._clock = clock
        self._sleep = sleep
        self._client: imaplib.IMAP4_SSL | None = None
        self._last_command_at: float | None = None

    def connect(self) -> None:
        if self._client is not None:
            return
        credentials = self._credentials()
        if not credentials.token:
            raise MailAuthenticationError("Gmail OAuth did not provide an access token.")
        client: imaplib.IMAP4_SSL | None = None
        try:
            client = self._imap_factory("imap.gmail.com", 993)
            auth = f"user={self._config.account}\x01auth=Bearer {credentials.token}\x01\x01"
            status, _ = self._command(client.authenticate, "XOAUTH2", lambda _: auth.encode())
        except (imaplib.IMAP4.error, OSError) as exc:
            if client is not None:
                self._close_client(client)
            raise MailConnectionError("Could not connect to Gmail IMAP.") from exc
        if status != "OK":
            self._close_client(client)
            raise MailAuthenticationError("Gmail XOAUTH2 authentication was rejected.")
        self._client = client

    def disconnect(self) -> None:
        if self._client is None:
            return
        try:
            self._command(self._client.logout)
        finally:
            self._client = None

    def get_provider_stats(self) -> MailProviderStats:
        all_mail = self._all_mailbox()
        all_count = self._select_count(all_mail)
        inbox_count = self._select_count("INBOX")
        inbox_unread = len(self._search("UNSEEN"))
        self._select(all_mail)
        oldest, newest = self._edge_dates(all_count)
        return MailProviderStats(all_count, inbox_count, inbox_unread, oldest, newest)

    def get_messages(self, category: str, since: datetime | None, before: datetime | None) -> list[MailMessage]:
        if category != "INBOX":
            raise ValueError("Gmail AP1 supports only category 'INBOX'.")
        since = self._utc_timestamp(since, "since")
        before = self._utc_timestamp(before, "before")
        if since is not None and before is not None and since >= before:
            raise ValueError("since must be earlier than before.")
        self._select("INBOX")
        identifiers = self._search("ALL")
        return [message for identifier in identifiers if (message := self._message(identifier, since, before)) is not None]

    def get_messages_by_thread(self, thread_id: str) -> list[MailMessage]:
        if not thread_id.strip():
            raise ValueError("thread_id must not be empty.")
        self._select(self._all_mailbox())
        return [self._message(identifier, None, None) for identifier in self._search("X-GM-THRID", thread_id)]  # type: ignore[list-item]

    def _credentials(self) -> Credentials:
        credentials: Credentials | None = None
        try:
            if self._config.oauth_token.is_file():
                credentials = Credentials.from_authorized_user_file(str(self._config.oauth_token), [_SCOPE])
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            if not credentials or not credentials.valid:
                flow = InstalledAppFlow.from_client_secrets_file(str(self._config.client_secret), [_SCOPE])
                credentials = flow.run_local_server(host="localhost", port=0, open_browser=True)
            self._store_token(credentials)
            return credentials
        except Exception as exc:
            raise MailAuthenticationError("Gmail OAuth authentication failed.") from exc

    def _store_token(self, credentials: Credentials) -> None:
        serialized = credentials.to_json()
        path = self._config.oauth_token
        if path.exists() and path.read_text(encoding="utf-8") == serialized:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized, encoding="utf-8")
        os.chmod(path, 0o600)

    def _client_or_raise(self) -> imaplib.IMAP4_SSL:
        if self._client is None:
            raise MailConnectionError("Gmail provider is not connected.")
        return self._client

    @staticmethod
    def _close_client(client: imaplib.IMAP4_SSL) -> None:
        try:
            client.logout()
        except (imaplib.IMAP4.error, OSError):
            pass

    def _command(self, method, *args):
        if self._last_command_at is not None:
            delay = 0.5 - (self._clock() - self._last_command_at)
            if delay > 0:
                self._sleep(delay)
        try:
            result = method(*args)
        except (imaplib.IMAP4.error, OSError) as exc:
            raise MailProtocolError("Gmail IMAP command failed.") from exc
        self._last_command_at = self._clock()
        return result

    def _select(self, mailbox: str) -> None:
        status, _ = self._command(self._client_or_raise().select, f'"{mailbox}"', True)
        if status != "OK":
            raise MailProtocolError(f"Could not select Gmail mailbox '{mailbox}'.")

    def _select_count(self, mailbox: str) -> int:
        status, data = self._command(self._client_or_raise().select, f'"{mailbox}"', True)
        if status != "OK" or not data or data[0] is None:
            raise MailProtocolError(f"Could not select Gmail mailbox '{mailbox}'.")
        return int(data[0])

    def _search(self, *criteria: str) -> list[bytes]:
        status, data = self._command(self._client_or_raise().search, None, *criteria)
        if status != "OK" or not data:
            raise MailProtocolError("Gmail IMAP search failed.")
        return data[0].split()

    def _all_mailbox(self) -> str:
        status, mailboxes = self._command(self._client_or_raise().list)
        if status != "OK" or not mailboxes:
            raise MailProtocolError("Could not discover Gmail All Mail mailbox.")
        matches = [line for line in mailboxes if line and b"\\All" in line.split(b")", 1)[0]]
        if len(matches) != 1:
            raise MailProtocolError("Gmail All Mail mailbox is ambiguous or unavailable.")
        match = _MAILBOX.search(matches[0])
        if match is None:
            raise MailProtocolError("Could not parse Gmail All Mail mailbox.")
        return match.group(1).decode("utf-8")

    def _edge_dates(self, count: int) -> tuple[datetime | None, datetime | None]:
        if count == 0:
            return None, None
        return self._internal_date(b"1"), self._internal_date(b"*")

    def _internal_date(self, identifier: bytes) -> datetime:
        status, data = self._command(self._client_or_raise().fetch, identifier, "(INTERNALDATE)")
        if status != "OK" or not data or not isinstance(data[0], tuple):
            raise MailProtocolError("Gmail did not return an INTERNALDATE.")
        match = _INTERNALDATE.search(data[0][0])
        if match is None:
            raise MailProtocolError("Gmail did not return an INTERNALDATE.")
        return parsedate_to_datetime(match.group(1).decode("ascii")).astimezone(timezone.utc)

    def _message(self, identifier: bytes, since: datetime | None, before: datetime | None) -> MailMessage | None:
        status, data = self._command(self._client_or_raise().fetch, identifier, "(X-GM-MSGID X-GM-THRID FLAGS INTERNALDATE BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
        if status != "OK" or not data or not isinstance(data[0], tuple):
            raise MailProtocolError("Gmail did not return message metadata.")
        metadata, headers = data[0]
        internal = self._parse_internal_date(metadata)
        if (since is not None and internal < since) or (before is not None and internal >= before):
            return None
        message_id = _MESSAGE_ID.search(metadata)
        if message_id is None:
            raise MailProtocolError("Gmail did not return X-GM-MSGID.")
        thread_id = _THREAD_ID.search(metadata)
        flags = _FLAGS.search(metadata)
        if flags is None:
            raise MailProtocolError("Gmail did not return FLAGS.")
        message = message_from_bytes(headers)
        return MailMessage(
            message_id=message_id.group(1).decode(),
            thread_id=thread_id.group(1).decode() if thread_id else None,
            internal_date=internal,
            subject=str(make_header(decode_header(message.get("Subject", "")))),
            sender=str(make_header(decode_header(message.get("From", "")))),
            is_read=b"\\Seen" in flags.group(1).split(),
        )

    @staticmethod
    def _parse_internal_date(metadata: bytes) -> datetime:
        match = _INTERNALDATE.search(metadata)
        if match is None:
            raise MailProtocolError("Gmail did not return an INTERNALDATE.")
        return parsedate_to_datetime(match.group(1).decode("ascii")).astimezone(timezone.utc)

    @staticmethod
    def _utc_timestamp(value: datetime | None, name: str) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{name} must include a timezone.")
        return value.astimezone(timezone.utc)
