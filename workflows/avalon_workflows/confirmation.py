"""Typed builder for Avalon workflow confirmation tables."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


_TYPE_NAMES = {
    str: "str",
    int: "int",
    float: "float",
    bool: "bool",
    date: "date",
    datetime: "datetime",
}
_SUPPORTED_TYPE_NAMES = frozenset(_TYPE_NAMES.values())
_RESERVED_KEYS = frozenset({"avalon_confirmation"})


@dataclass(frozen=True, slots=True)
class _ConfirmationColumn:
    name: str
    type_name: str
    nullable: bool
    editable: bool
    visible: bool
    label: str


class ConfirmationRows:
    """Fluent row builder bound to one confirmation table."""

    def __init__(self, table: "ConfirmationTable") -> None:
        self._table = table
        self._rows: list[dict[str, object]] = []

    def add(
        self,
        values: list[object] | None = None,
        **named_values: object,
    ) -> "ConfirmationRows":
        if values is not None and named_values:
            raise ValueError("Provide row values either as a list or as named values.")

        if values is None and not named_values:
            raise ValueError("Row values must not be empty.")

        columns = self._table._columns
        if not columns:
            raise ValueError("Add at least one column before adding rows.")

        if values is not None:
            if len(values) != len(columns):
                raise ValueError(
                    f"Expected {len(columns)} row values, got {len(values)}."
                )
            row = {
                column.name: value
                for column, value in zip(columns, values, strict=True)
            }
        else:
            expected = {column.name for column in columns}
            provided = set(named_values)
            missing = expected - provided
            unknown = provided - expected

            if missing:
                raise ValueError(
                    f"Missing row values: {', '.join(sorted(missing))}."
                )
            if unknown:
                raise ValueError(
                    f"Unknown row values: {', '.join(sorted(unknown))}."
                )

            row = dict(named_values)

        self._rows.append(self._table._validate_row(row))
        return self

    def _to_list(self) -> list[dict[str, object]]:
        return [dict(row) for row in self._rows]


class ConfirmationTable:
    """Build a validated Avalon workflow confirmation table."""

    def __init__(self, title: str) -> None:
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Confirmation table title must be a non-empty string.")

        self.title = title
        self._columns: list[_ConfirmationColumn] = []
        self.rows = ConfirmationRows(self)

    def column(
        self,
        name: str,
        type: type[Any] | str,
        *,
        nullable: bool = False,
        editable: bool = False,
        visible: bool = True,
        label: str | None = None,
    ) -> "ConfirmationTable":
        if self.rows._rows:
            raise ValueError("Cannot add columns after rows have been added.")

        if not isinstance(name, str) or not name:
            raise ValueError("Column name must be a non-empty string.")
        if name in _RESERVED_KEYS:
            raise ValueError(f"Column name '{name}' is reserved for Avalon.")
        if any(column.name == name for column in self._columns):
            raise ValueError(f"Column '{name}' already exists.")

        type_name = self._type_name(type)

        if not isinstance(nullable, bool):
            raise TypeError("nullable must be bool.")
        if not isinstance(editable, bool):
            raise TypeError("editable must be bool.")
        if not isinstance(visible, bool):
            raise TypeError("visible must be bool.")
        if label is not None and not isinstance(label, str):
            raise TypeError("label must be str or None.")

        self._columns.append(
            _ConfirmationColumn(
                name=name,
                type_name=type_name,
                nullable=nullable,
                editable=editable,
                visible=visible,
                label=name if label is None else label,
            )
        )
        return self

    def to_dict(self) -> dict[str, object]:
        if not self._columns:
            raise ValueError("Confirmation table must contain at least one column.")
        if not self.rows._rows:
            raise ValueError("Confirmation table must contain at least one row.")

        return {
            "schema": {
                "title": self.title,
                "columns": [
                    {
                        "key": column.name,
                        "type": column.type_name,
                        "nullable": column.nullable,
                        "editable": column.editable,
                        "visible": column.visible,
                        "label": column.label,
                    }
                    for column in self._columns
                ],
            },
            "rows": self.rows._to_list(),
        }

    @staticmethod
    def _type_name(value: type[Any] | str) -> str:
        if isinstance(value, str):
            if value not in _SUPPORTED_TYPE_NAMES:
                raise ValueError(f"Unsupported confirmation column type '{value}'.")
            return value

        type_name = _TYPE_NAMES.get(value)
        if type_name is None:
            raise ValueError(f"Unsupported confirmation column type '{value}'.")
        return type_name

    def _validate_row(self, row: dict[str, object]) -> dict[str, object]:
        validated: dict[str, object] = {}

        for column in self._columns:
            value = row[column.name]

            if value is None:
                if not column.nullable:
                    raise ValueError(f"'{column.name}' must not be null.")
                validated[column.name] = None
                continue

            validated[column.name] = self._validate_value(value, column)

        return validated

    @staticmethod
    def _validate_value(value: object, column: _ConfirmationColumn) -> object:
        if column.type_name == "str":
            if not isinstance(value, str):
                raise TypeError(f"'{column.name}' must be str.")
            return value

        if column.type_name == "int":
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"'{column.name}' must be int.")
            return value

        if column.type_name == "float":
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"'{column.name}' must be float.")
            return value

        if column.type_name == "bool":
            if not isinstance(value, bool):
                raise TypeError(f"'{column.name}' must be bool.")
            return value

        if column.type_name == "date":
            if isinstance(value, datetime):
                raise TypeError(f"'{column.name}' must be date.")
            if isinstance(value, date):
                return value.isoformat()
            if isinstance(value, str):
                try:
                    date.fromisoformat(value)
                except ValueError as exc:
                    raise TypeError(f"'{column.name}' must be an ISO date.") from exc
                return value
            raise TypeError(f"'{column.name}' must be date.")

        if column.type_name == "datetime":
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, str):
                try:
                    if "T" not in value:
                        raise ValueError
                    datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError as exc:
                    raise TypeError(
                        f"'{column.name}' must be an ISO datetime."
                    ) from exc
                return value
            raise TypeError(f"'{column.name}' must be datetime.")

        raise AssertionError(f"Unhandled confirmation column type '{column.type_name}'.")
