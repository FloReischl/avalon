from dataclasses import dataclass
import re


_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class CommandRequest:
    key: str
    payload: str


def parse_command(text: str) -> CommandRequest | None:
    stripped = text.lstrip()

    parts = stripped.split(None, 2)
    if not parts or parts[0].lower() != "/command":
        return None

    if len(parts) < 2:
        return CommandRequest(key="", payload="")

    key = parts[1]
    if not _IDENTIFIER_PATTERN.fullmatch(key):
        return CommandRequest(key="", payload="")

    payload = parts[2] if len(parts) == 3 else ""
    return CommandRequest(key=key.lower(), payload=payload)
