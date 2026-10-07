import pytest

from helpers import mailbox_connect, latest_message_ids, fetch_message, text_body, decode_header


def test_read_latest_10_message_headers() -> None:
    client = mailbox_connect()

    try:
        message_ids = latest_message_ids(client, limit=10)
        assert message_ids, "INBOX contains no messages"

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


def test_read_latest_message_body() -> None:
    client = mailbox_connect()

    try:
        message_ids = latest_message_ids(client, limit=1)
        assert message_ids, "INBOX contains no messages"

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

        assert body.strip(), "Latest message contains no text body"
    finally:
        client.logout()

if __name__ == "__main__":
    # Führt alle Tests in genau dieser Datei aus (__file__)
    pytest.main([__file__, "-v", "-s", "--capture=no"])
