from dataclasses import dataclass
import re


_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class CommandRequest:
    key: str
    payload: str


def parse_command(text: str) -> CommandRequest | None:
    stripped = text.lstrip()

    parts = stripped.split(None, 1)
    if not parts:
        return None

    identifier = parts[0]
    if (
        not identifier.startswith("/")
        or not _IDENTIFIER_PATTERN.fullmatch(identifier[1:])
    ):
        return None

    payload = parts[1] if len(parts) == 2 else ""
    return CommandRequest(key=identifier[1:], payload=payload)
