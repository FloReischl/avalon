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
    if len(parts) < 2:
        return None

    group = parts[0]
    if not group.startswith("/") or not _IDENTIFIER_PATTERN.fullmatch(group[1:]):
        return None

    command = parts[1]
    if not _IDENTIFIER_PATTERN.fullmatch(command):
        return None

    key = f"{group[1:].lower()}_{command.lower()}"
    payload = parts[2] if len(parts) == 3 else ""
    return CommandRequest(key=key, payload=payload)
