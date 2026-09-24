"""Small transport-neutral authorization value objects."""

from dataclasses import dataclass


PERMANENT_VALID_TO_YEAR = 2040


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    id: str
    context: str
    key: str
    formatted_items: list[str]
    items: list[object]
    validity_type: str
    default_expiry: int


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    approved_item_indexes: list[int]
    duration_seconds: int | None = None
