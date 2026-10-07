import email
import imaplib
import os
from email.header import make_header, decode_header as inner_decode_header
from email.message import Message


IMAP_HOST = "imap.mailbox.org"
IMAP_PORT = 993

MAILBOX_USER = "AVALON_MAILBOX_ORG_USER"
MAILBOX_PASSWORD = "AVALON_MAILBOX_ORG_PASSWORD"


def mailbox_credentials() -> tuple[str, str]:
    user = os.environ.get(MAILBOX_USER)
    password = os.environ.get(MAILBOX_PASSWORD)

    assert user, f"{MAILBOX_USER} is not set"
    assert password, f"{MAILBOX_PASSWORD} is not set"

    return user, password


def mailbox_connect() -> imaplib.IMAP4_SSL:
    user, password = mailbox_credentials()

    client = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    client.login(user, password)

    status, _ = client.select("INBOX", readonly=True)
    assert status == "OK"

    return client


def decode_header(value: str | None) -> str:
    if not value:
        return ""
    return str(make_header(inner_decode_header(value)))


def latest_message_ids(
    client: imaplib.IMAP4_SSL,
    limit: int,
) -> list[bytes]:
    status, data = client.search(None, "ALL")
    assert status == "OK"
    assert data

    message_ids = data[0].split()
    return message_ids[-limit:][::-1]


def fetch_message(
    client: imaplib.IMAP4_SSL,
    message_id: bytes,
    query: str,
) -> Message:
    status, data = client.fetch(message_id, query)
    assert status == "OK"
    assert data
    assert isinstance(data[0], tuple)

    raw_message = data[0][1]
    assert isinstance(raw_message, bytes)

    return email.message_from_bytes(raw_message)


def is_text_content(content_type: str) -> bool:
    return content_type.casefold() in [ "text/plain", "text/html" ]


def text_body(message: Message) -> str:
    if message.is_multipart():
        for part in message.walk():
            if not is_text_content(part.get_content_type()):
                continue
            if "attachment" in (part.get("Content-Disposition") or "").lower():
                continue

            payload = part.get_payload(decode=True)
            if payload is None:
                continue

            charset = part.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")

        return ""

    payload = message.get_payload(decode=True) if is_text_content(message.get_content_type()) else None
    if payload is None:
        return ""

    charset = message.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")
