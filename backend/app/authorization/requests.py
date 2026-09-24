"""In-memory waiting room for one-shot authorization decisions."""

import asyncio
from dataclasses import dataclass
from uuid import uuid4

from app.authorization.exceptions import AbortException, AuthorizationTimeout
from app.authorization.types import AuthorizationDecision, AuthorizationRequest


@dataclass(slots=True)
class _PendingRequest:
    request: AuthorizationRequest
    future: asyncio.Future[AuthorizationDecision]


class AuthorizationRequestManager:
    """Publish requests and await a browser decision for at most ten minutes."""

    def __init__(self, timeout_seconds: float = 600.0) -> None:
        self._timeout_seconds = timeout_seconds
        self._pending: dict[str, _PendingRequest] = {}

    def create(
        self,
        context: str,
        key: str,
        items: list[object],
        formatted_items: list[str],
        validity_type: str,
        default_expiry: int,
    ) -> AuthorizationRequest:
        if len(items) != len(formatted_items):
            raise ValueError("Authorization items must have matching labels.")
        request = AuthorizationRequest(
            id=uuid4().hex,
            context=context,
            key=key,
            items=items,
            formatted_items=formatted_items,
            validity_type=validity_type,
            default_expiry=default_expiry,
        )
        self._pending[request.id] = _PendingRequest(
            request=request,
            future=asyncio.get_running_loop().create_future(),
        )
        return request

    async def wait(self, request_id: str) -> AuthorizationDecision:
        pending = self._get(request_id)
        try:
            return await asyncio.wait_for(
                asyncio.shield(pending.future), timeout=self._timeout_seconds
            )
        except TimeoutError as exc:
            raise AuthorizationTimeout() from exc
        finally:
            self._pending.pop(request_id, None)

    def confirm(
        self,
        request_id: str,
        approved_item_indexes: list[int],
        duration_seconds: int | None,
    ) -> None:
        pending = self._get(request_id)
        if len(set(approved_item_indexes)) != len(approved_item_indexes):
            raise ValueError("Approved item indexes must be unique.")
        if any(index < 0 or index >= len(pending.request.items) for index in approved_item_indexes):
            raise ValueError("Approved item index is outside the request.")
        if pending.request.validity_type == "permanent":
            if duration_seconds is not None:
                raise ValueError("Permanent grants do not accept a duration.")
        elif duration_seconds is None or not 1 <= duration_seconds <= 365 * 24 * 60 * 60:
            raise ValueError("Duration must be between one second and 365 days.")
        if not pending.future.done():
            pending.future.set_result(
                AuthorizationDecision(approved_item_indexes, duration_seconds)
            )

    def abort(self, request_id: str) -> None:
        pending = self._get(request_id)
        if not pending.future.done():
            pending.future.set_exception(AbortException())

    def _get(self, request_id: str) -> _PendingRequest:
        pending = self._pending.get(request_id)
        if pending is None:
            raise KeyError("Authorization request does not exist or has expired.")
        return pending
