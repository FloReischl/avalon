"""Transport-neutral orchestration of capability authorization."""

import json
from datetime import datetime, timedelta
from typing import Awaitable, Callable, TypeVar

from app.authorization.exceptions import PermissionDenied
from app.authorization.permissions import PermissionRegistry
from app.authorization.requests import AuthorizationRequestManager
from app.authorization.types import PERMANENT_VALID_TO_YEAR, AuthorizationRequest
from app.persistence.authorization_repository import AuthorizationRepository


Result = TypeVar("Result")
RequestObserver = Callable[[AuthorizationRequest], None]


class PermissionGuard:
    """Authorize one complete capability call for one trusted principal."""

    def __init__(
        self,
        repository: AuthorizationRepository,
        registry: PermissionRegistry,
        requests: AuthorizationRequestManager,
        request_observer: RequestObserver | None = None,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._repository = repository
        self._registry = registry
        self._requests = requests
        self._request_observer = request_observer
        self._clock = clock

    async def execute(
        self,
        principal_id: int,
        context: str,
        key: str,
        items: list[object],
        capability: Callable[[list[object]], Awaitable[Result]],
        source_label: str = "Chat: chat-default",
        permission_catalog_id: int | None = None,
    ) -> Result:
        definition = (
            self._repository.get_principal_permission_by_catalog_id(
                principal_id, permission_catalog_id
            )
            if permission_catalog_id is not None
            else self._repository.get_principal_permission(principal_id, context, key)
        )
        if definition is None:
            raise PermissionDenied(f"{context}/{key} is not grantable for principal.")
        permission = self._registry.get(context, key)
        if not permission.allows(definition, items):
            raise PermissionDenied(f"{context}/{key} is not allowed by principal scope.")
        now = self._clock()
        for grant in self._repository.get_grants(definition.id):
            if permission.check(definition, grant, items, now):
                return await capability(items)

        request = self._requests.create(
            context,
            key,
            items,
            [permission.format(item) for item in items],
            definition.validity_type,
            definition.default_expiry,
            source_label,
        )
        if self._request_observer is not None:
            self._request_observer(request)
        decision = await self._requests.wait(request.id)
        approved_items = [items[index] for index in decision.approved_item_indexes]
        valid_to = self._valid_to(definition.validity_type, decision.duration_seconds, now)
        item_range = (
            json.dumps(approved_items, ensure_ascii=False, separators=(",", ":"))
            if definition.validity_type == "range"
            else None
        )
        self._repository.create_grant(definition.id, now, valid_to, item_range)
        return await capability(approved_items)

    @staticmethod
    def _valid_to(validity_type: str, duration_seconds: int | None, now: datetime) -> datetime:
        if validity_type == "permanent":
            return datetime(PERMANENT_VALID_TO_YEAR, 1, 1)
        assert duration_seconds is not None
        return now + timedelta(seconds=duration_seconds)
