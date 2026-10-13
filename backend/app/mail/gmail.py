"""Gmail's IMAP/XOAUTH2 implementation of the mail provider contract."""

from __future__ import annotations

import base64
import binascii
import imaplib
import os
import re
import time
from datetime import datetime, timezone
from email import message_from_bytes
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime
from typing import Callable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from app.mail.models import (
    Mail,
    MailAttachment,
    MailBodyPart,
    MailMessage,
    MailProviderStats,
    MailSender,
)
from app.mail.providers import MailAuthenticationError, MailConnectionError, MailProtocolError
from app.user_config import GoogleMailUserConfig


_SCOPE = "https://mail.google.com/"
_INTERNALDATE = re.compile(rb'INTERNALDATE "([^"]+)"')
_MESSAGE_ID = re.compile(rb"X-GM-MSGID (\d+)")
_THREAD_ID = re.compile(rb"X-GM-THRID (\d+)")
_FLAGS = re.compile(rb"FLAGS \(([^)]*)\)")
_MAILBOX = re.compile(rb' (?:"((?:[^"\\]|\\.)*)"|([^ ]+))$')
_VALID_MESSAGE_ID = re.compile(r"[0-9]+$")


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
        since = self._utc_timestamp(since)
        before = self._utc_timestamp(before)
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

    def get_mail(self, message_id: str) -> Mail:
        if _VALID_MESSAGE_ID.fullmatch(message_id) is None:
            raise ValueError("message_id must be a Gmail message ID returned by get_messages.")
        self._select(self._all_mailbox())
        identifiers = self._search("X-GM-MSGID", message_id)
        if not identifiers:
            raise MailProtocolError("Gmail message ID was not found.")
        status, data = self._command(
            self._client_or_raise().fetch,
            identifiers[0],
            "(X-GM-MSGID X-GM-THRID FLAGS INTERNALDATE BODY.PEEK[])",
        )
        if status != "OK" or not data or not isinstance(data[0], tuple):
            raise MailProtocolError("Gmail did not return the requested message.")
        metadata, raw_message = data[0]
        return self._mail(metadata, raw_message)

    def get_categories(self) -> list[str]:
        status, mailboxes = self._command(self._client_or_raise().list)
        if status != "OK" or mailboxes is None:
            raise MailProtocolError("Could not list Gmail labels.")
        return [self._parse_mailbox_name(mailbox) for mailbox in mailboxes if mailbox]

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
        return self._parse_mailbox_name(matches[0])

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

    def _mail(self, metadata: bytes, raw_message: bytes) -> Mail:
        message_id = _MESSAGE_ID.search(metadata)
        if message_id is None:
            raise MailProtocolError("Gmail did not return X-GM-MSGID.")
        flags = _FLAGS.search(metadata)
        if flags is None:
            raise MailProtocolError("Gmail did not return FLAGS.")
        thread_id = _THREAD_ID.search(metadata)
        message = message_from_bytes(raw_message)
        sender_name, sender_email = parseaddr(str(make_header(decode_header(message.get("From", "")))))
        body, attachments = self._content_parts(message)
        return Mail(
            message_id=message_id.group(1).decode(),
            is_read=b"\\Seen" in flags.group(1).split(),
            internal_date=self._parse_internal_date(metadata),
            subject=str(make_header(decode_header(message.get("Subject", "")))),
            sender=MailSender(name=sender_name, email_address=sender_email),
            thread_id=thread_id.group(1).decode() if thread_id else None,
            body=body,
            attachments=attachments,
        )

    @staticmethod
    def _content_parts(message) -> tuple[list[MailBodyPart], list[MailAttachment]]:
        body: list[MailBodyPart] = []
        attachments: list[MailAttachment] = []
        next_index = 0

        def visit(part, is_root: bool = False) -> None:
            nonlocal next_index
            index = next_index
            next_index += 1
            disposition = part.get_content_disposition()
            filename = part.get_filename()
            if not is_root and (
                disposition == "attachment"
                or filename is not None
                or part.get_content_type() == "message/rfc822"
            ):
                attachments.append(
                    MailAttachment(name=filename or "", id=str(index), mime_type=part.get_content_type())
                )
                return
            if part.is_multipart():
                for child in part.get_payload():
                    visit(child)
                return
            if part.get_content_type() not in {"text/plain", "text/html"}:
                return
            try:
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                content = payload.decode(charset)
            except (binascii.Error, LookupError, TypeError, UnicodeError, ValueError):
                return
            body.append(MailBodyPart(mime_type=part.get_content_type(), content=content))

        visit(message, is_root=True)
        return body, attachments

    @staticmethod
    def _parse_mailbox_name(mailbox: bytes) -> str:
        match = _MAILBOX.search(mailbox)
        if match is None:
            raise MailProtocolError("Could not parse Gmail mailbox name.")
        encoded = match.group(1) if match.group(1) is not None else match.group(2)
        assert encoded is not None
        return GmailMailProvider._decode_modified_utf7(
            GmailMailProvider._unescape_mailbox_name(encoded)
        )

    @staticmethod
    def _unescape_mailbox_name(value: bytes) -> bytes:
        result = bytearray()
        position = 0
        while position < len(value):
            character = value[position]
            if character != ord("\\"):
                result.append(character)
                position += 1
                continue
            position += 1
            if position == len(value) or value[position] not in (ord('"'), ord("\\")):
                raise MailProtocolError("Could not parse Gmail mailbox name.")
            result.append(value[position])
            position += 1
        return bytes(result)

    @staticmethod
    def _decode_modified_utf7(value: bytes) -> str:
        """Decode the modified UTF-7 mailbox representation used by IMAP."""
        result: list[str] = []
        position = 0
        try:
            while position < len(value):
                marker = value.find(b"&", position)
                if marker < 0:
                    result.append(value[position:].decode("ascii"))
                    break
                result.append(value[position:marker].decode("ascii"))
                end = value.find(b"-", marker)
                if end < 0:
                    raise MailProtocolError("Could not decode Gmail mailbox name.")
                encoded = value[marker + 1:end]
                if not encoded:
                    result.append("&")
                else:
                    padding = b"=" * (-len(encoded) % 4)
                    decoded = base64.b64decode(
                        encoded.replace(b",", b"/") + padding,
                        validate=True,
                    )
                    result.append(decoded.decode("utf-16-be"))
                position = end + 1
        except (binascii.Error, UnicodeDecodeError, ValueError):
            raise MailProtocolError("Could not decode Gmail mailbox name.") from None
        return "".join(result)

    @staticmethod
    def _parse_internal_date(metadata: bytes) -> datetime:
        match = _INTERNALDATE.search(metadata)
        if match is None:
            raise MailProtocolError("Gmail did not return an INTERNALDATE.")
        return parsedate_to_datetime(match.group(1).decode("ascii")).astimezone(timezone.utc)

    @staticmethod
    def _utc_timestamp(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.astimezone(timezone.utc)
