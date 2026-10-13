import imaplib
import json
import os
import re
from pathlib import Path

import pytest
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from helpers import (
    decode_header,
    fetch_message,
    latest_message_ids,
    text_body,
)


GMAIL_CLIENT_SECRET_ENV = "AVALON_GMAIL_CLIENT_SECRET"
GMAIL_SCOPE = "https://mail.google.com/"

GMAIL_IMAP_HOST = "imap.gmail.com"
GMAIL_IMAP_PORT = 993

TOKEN_PATH = Path.home() / ".avalon" / "security" / "gmail-token.json"


def gmail_client_config() -> dict:
    raw_config = os.environ.get(GMAIL_CLIENT_SECRET_ENV)
    assert raw_config, f"{GMAIL_CLIENT_SECRET_ENV} is not set"

    config = json.loads(raw_config)
    assert "installed" in config, "Gmail OAuth client must be a Desktop application"

    return config


def load_gmail_credentials() -> Credentials:
    credentials = None

    if TOKEN_PATH.exists():
        credentials = Credentials.from_authorized_user_file(
            TOKEN_PATH,
            scopes=[GMAIL_SCOPE],
        )

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_config(
            gmail_client_config(),
            scopes=[GMAIL_SCOPE],
        )
        credentials = flow.run_local_server(
            host="localhost",
            port=0,
            open_browser=True,
        )

    if not TOKEN_PATH.exists() or credentials.to_json() != TOKEN_PATH.read_text():
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(credentials.to_json())
        TOKEN_PATH.chmod(0o600)

    return credentials


def gmail_connect() -> imaplib.IMAP4_SSL:
    credentials = load_gmail_credentials()

    assert credentials.token, "Google OAuth access token is missing"

    client = imaplib.IMAP4_SSL(
        GMAIL_IMAP_HOST,
        GMAIL_IMAP_PORT,
    )

    # Google credentials do not reliably contain the Gmail address.
    # Obtain it from the OAuth user info is deliberately outside this spike.
    gmail_user = os.environ.get("AVALON_GMAIL_USER")
    assert gmail_user, "AVALON_GMAIL_USER is not set"

    auth_string = (
        f"user={gmail_user}\x01"
        f"auth=Bearer {credentials.token}\x01\x01"
    )

    client.authenticate(
        "XOAUTH2",
        lambda _: auth_string.encode("utf-8"),
    )

    status, _ = client.select("INBOX", readonly=True)
    assert status == "OK"

    return client

# @pytest.mark.skip(reason="works")
def test_read_latest_10_gmail_headers() -> None:
    client = gmail_connect()

    try:
        message_ids = latest_message_ids(client, limit=10)
        assert message_ids, "Gmail INBOX contains no messages"

        for message_id in message_ids:
            message = fetch_message(
                client,
                message_id,
                "(BODY.PEEK[HEADER.FIELDS (DATE FROM SUBJECT)])",
            )

            print()
            print(f"Date:    {decode_header(message.get('Date'))}")
            print(f"From:    {decode_header(message.get('From'))}")
            print(f"Subject: {decode_header(message.get('Subject'))}")
    finally:
        client.logout()


def gmail_all_mailbox(client: imaplib.IMAP4_SSL) -> str:
    status, mailboxes = client.list()
    assert status == "OK"
    assert mailboxes

    all_mailboxes = [
        mailbox
        for mailbox in mailboxes
        if mailbox is not None and b"\\All" in mailbox.split(b")", 1)[0]
    ]
    assert len(all_mailboxes) == 1

    match = re.search(rb' "/" "(.+)"$', all_mailboxes[0])
    assert match, f"Cannot parse Gmail All mailbox: {all_mailboxes[0]!r}"

    return match.group(1).decode("utf-8")


def test_add_and_remove_gmail_label() -> None:
    client = gmail_connect()
    all_mail_message_id = None

    try:
        status, capabilities = client.capability()
        assert status == "OK"
        assert any(b"X-GM-EXT-1" in item for item in capabilities)

        status, _ = client.select('"Avalon/Test"', readonly=True)
        assert status == "OK"

        message_ids = latest_message_ids(client, limit=1)
        assert message_ids, "Gmail label Avalon/Test contains no messages"

        status, data = client.fetch(
            message_ids[0],
            "(X-GM-MSGID)",
        )
        assert status == "OK"
        assert data

        response = data[0]
        assert isinstance(response, bytes)

        match = re.search(rb"X-GM-MSGID (\d+)", response)
        assert match, "X-GM-MSGID missing"
        gmail_message_id = match.group(1)

        all_mailbox = gmail_all_mailbox(client)

        status, _ = client.select(f'"{all_mailbox}"', readonly=False)
        assert status == "OK"

        status, data = client.search(
            None,
            "X-GM-MSGID",
            gmail_message_id.decode(),
        )
        assert status == "OK"
        assert data and data[0]

        all_mail_ids = data[0].split()
        assert len(all_mail_ids) == 1
        all_mail_message_id = all_mail_ids[0]

        status, _ = client.store(
            all_mail_message_id,
            "+X-GM-LABELS",
            '"Avalon/Test2"',
        )
        assert status == "OK"

        status, data = client.fetch(
            all_mail_message_id,
            "(X-GM-LABELS)",
        )
        assert status == "OK"
        assert data

        labels_after_add = data[0]
        assert isinstance(labels_after_add, bytes)
        assert b"Avalon/Test" in labels_after_add
        assert b"Avalon/Test2" in labels_after_add

        status, _ = client.store(
            all_mail_message_id,
            "-X-GM-LABELS",
            '"Avalon/Test2"',
        )
        assert status == "OK"

        status, data = client.fetch(
            all_mail_message_id,
            "(X-GM-LABELS)",
        )
        assert status == "OK"
        assert data

        labels_after_remove = data[0]
        assert isinstance(labels_after_remove, bytes)
        assert b"Avalon/Test" in labels_after_remove
        assert b"Avalon/Test2" not in labels_after_remove
    finally:
        if all_mail_message_id is not None:
            client.store(
                all_mail_message_id,
                "-X-GM-LABELS",
                '"Avalon/Test2"',
            )
        client.logout()


@pytest.mark.skip(reason="works")
def test_read_latest_gmail_body() -> None:
    client = gmail_connect()

    try:
        message_ids = latest_message_ids(client, limit=1)
        assert message_ids, "Gmail INBOX contains no messages"

        message = fetch_message(
            client,
            message_ids[0],
            "(BODY.PEEK[])",
        )
        body = text_body(message)

        print()
        print(f"Subject: {decode_header(message.get('Subject'))}")
        print()
        print(body[:300])

        assert body.strip(), "Latest Gmail message contains no text body"
    finally:
        client.logout()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--capture=no"])