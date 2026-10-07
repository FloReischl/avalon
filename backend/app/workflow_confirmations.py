"""Process-local waiting room for one workflow confirmation."""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from uuid import uuid4


logger = logging.getLogger(__name__)

_TYPES = frozenset({"str", "int", "float", "bool", "date", "datetime"})
_DECISIONS = frozenset({"approved", "rejected"})


class ConfirmationCancelled(Exception):
    """The workflow user explicitly cancelled its confirmation."""


class ConfirmationValidationError(ValueError):
    """A confirmation input or final result violates its schema contract."""


@dataclass(frozen=True, slots=True)
class ConfirmationColumn:
    key: str
    type: str
    nullable: bool
    editable: bool
    visible: bool
    label: str | None


@dataclass(frozen=True, slots=True)
class WorkflowConfirmation:
    id: str
    execution_id: int
    schema: dict[str, object]
    columns: tuple[ConfirmationColumn, ...]
    rows: list[dict[str, object]]


@dataclass(slots=True)
class _PendingConfirmation:
    confirmation: WorkflowConfirmation
    future: asyncio.Future[list[dict[str, object]]]


class WorkflowConfirmationManager:
    """Keep the single in-memory workflow confirmation until it is resolved."""

    def __init__(self) -> None:
        self._pending: _PendingConfirmation | None = None
        self._listeners: set[asyncio.Queue[None]] = set()

    def create(
        self, execution_id: int, schema: object, rows: object
    ) -> WorkflowConfirmation:
        if self._pending is not None:
            raise ConfirmationValidationError("A workflow confirmation is already pending.")
        columns = _validate_schema(schema)
        initial_rows = _validate_rows(rows, columns, input_phase=True)
        confirmation = WorkflowConfirmation(
            id=uuid4().hex,
            execution_id=execution_id,
            schema=schema,
            columns=columns,
            rows=[{**row, "avalon_confirmation": "unconfirmed"} for row in initial_rows],
        )
        self._pending = _PendingConfirmation(
            confirmation=confirmation,
            future=asyncio.get_running_loop().create_future(),
        )
        self._notify()
        logger.info("[workflow-confirmation] requested execution_id=%s", execution_id)
        return confirmation

    async def wait(self, confirmation_id: str) -> list[dict[str, object]]:
        pending = self._get(confirmation_id)
        try:
            return await asyncio.shield(pending.future)
        finally:
            if self._pending is pending:
                self._pending = None
                self._notify()

    def pending(self) -> WorkflowConfirmation | None:
        return self._pending.confirmation if self._pending is not None else None

    def subscribe(self) -> asyncio.Queue[None]:
        queue: asyncio.Queue[None] = asyncio.Queue(maxsize=1)
        self._listeners.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[None]) -> None:
        self._listeners.discard(queue)

    def _notify(self) -> None:
        for queue in self._listeners:
            if queue.empty():
                queue.put_nowait(None)

    def confirm(self, confirmation_id: str, rows: list[dict[str, object]]) -> None:
        pending = self._get(confirmation_id)
        _validate_submission(pending.confirmation, rows)
        if not pending.future.done():
            pending.future.set_result(rows)
            self._notify()
            logger.info("[workflow-confirmation] confirmed execution_id=%s", pending.confirmation.execution_id)

    def cancel(self, confirmation_id: str) -> None:
        pending = self._get(confirmation_id)
        if not pending.future.done():
            pending.future.set_exception(ConfirmationCancelled())
            self._notify()
            logger.info("[workflow-confirmation] cancelled execution_id=%s", pending.confirmation.execution_id)

    def _get(self, confirmation_id: str) -> _PendingConfirmation:
        if self._pending is None or self._pending.confirmation.id != confirmation_id:
            raise KeyError("Workflow confirmation does not exist or has already been resolved.")
        return self._pending


def _validate_schema(schema: object) -> tuple[ConfirmationColumn, ...]:
    if not isinstance(schema, dict):
        raise ConfirmationValidationError("schema must be an object.")
    title = schema.get("title")
    columns = schema.get("columns")
    if not isinstance(title, str) or not title.strip():
        raise ConfirmationValidationError("schema.title must be a non-empty string.")
    if not isinstance(columns, list):
        raise ConfirmationValidationError("schema.columns must be a list.")
    parsed: list[ConfirmationColumn] = []
    keys: set[str] = set()
    for value in columns:
        if not isinstance(value, dict):
            raise ConfirmationValidationError("Every schema column must be an object.")
        key, type_name = value.get("key"), value.get("type")
        if not isinstance(key, str) or not key:
            raise ConfirmationValidationError("Every schema column needs a non-empty key.")
        if key in keys:
            raise ConfirmationValidationError("Schema column keys must be unique.")
        if type_name not in _TYPES:
            raise ConfirmationValidationError("Schema column type is unsupported.")
        flags = ("nullable", "editable", "visible")
        if any(not isinstance(value.get(flag), bool) for flag in flags):
            raise ConfirmationValidationError("Column nullable, editable and visible must be booleans.")
        label = value.get("label")
        if label is not None and not isinstance(label, str):
            raise ConfirmationValidationError("Column label must be a string when provided.")
        keys.add(key)
        parsed.append(ConfirmationColumn(key, type_name, value["nullable"], value["editable"], value["visible"], label))
    return tuple(parsed)


def _validate_rows(
    rows: object, columns: tuple[ConfirmationColumn, ...], *, input_phase: bool
) -> list[dict[str, object]]:
    if not isinstance(rows, list):
        raise ConfirmationValidationError("rows must be a list.")
    validated: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ConfirmationValidationError("Every row must be an object.")
        if input_phase and "avalon_confirmation" in row:
            raise ConfirmationValidationError("avalon_confirmation is reserved for Avalon.")
        for column in columns:
            if column.key not in row:
                raise ConfirmationValidationError(f"Row is missing required field '{column.key}'.")
            _validate_value(row[column.key], column)
        validated.append(row)
    return validated


def _validate_value(value: object, column: ConfirmationColumn) -> None:
    if value is None:
        if not column.nullable:
            raise ConfirmationValidationError(f"'{column.key}' must not be null.")
        return
    matches = {
        "str": isinstance(value, str),
        "int": isinstance(value, int) and not isinstance(value, bool),
        "float": isinstance(value, (int, float)) and not isinstance(value, bool),
        "bool": isinstance(value, bool),
        "date": isinstance(value, str) and _is_date(value),
        "datetime": isinstance(value, str) and _is_datetime(value),
    }
    if not matches[column.type]:
        raise ConfirmationValidationError(f"'{column.key}' does not match type {column.type}.")


def _is_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _is_datetime(value: str) -> bool:
    try:
        return "T" in value and isinstance(datetime.fromisoformat(value.replace("Z", "+00:00")), datetime)
    except ValueError:
        return False


def _validate_submission(confirmation: WorkflowConfirmation, rows: object) -> None:
    final_rows = _validate_rows(rows, confirmation.columns, input_phase=False)
    if len(final_rows) != len(confirmation.rows):
        raise ConfirmationValidationError("Confirmation rows must not be added or removed.")
    readonly = tuple(column for column in confirmation.columns if not column.editable)
    if _readonly_projections(final_rows, readonly) != _readonly_projections(confirmation.rows, readonly):
        raise ConfirmationValidationError("Read-only row values must not change.")
    for row in final_rows:
        if row.get("avalon_confirmation") not in _DECISIONS:
            raise ConfirmationValidationError("Every row must be approved or rejected.")


def _readonly_projections(rows: list[dict[str, object]], columns: tuple[ConfirmationColumn, ...]) -> Counter[tuple[object, ...]]:
    return Counter(tuple(row[column.key] for column in columns) for row in rows)


_manager = WorkflowConfirmationManager()


def get_workflow_confirmation_manager() -> WorkflowConfirmationManager:
    return _manager
