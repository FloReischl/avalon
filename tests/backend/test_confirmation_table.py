"""Focused contracts for the workflow confirmation table builder."""

from datetime import date, datetime

import pytest

from avalon_workflows import ConfirmationTable


def test_confirmation_table_builds_expected_payload_with_defaults() -> None:
    table = (
        ConfirmationTable("Podcast selection")
        .column("title", str)
        .column("url", "str", editable=True, label="URL")
        .column("publish", bool, visible=False)
    )

    table.rows.add(["First", "https://example.test/1", True]).add(
        title="Second",
        url="https://example.test/2",
        publish=False,
    )

    assert table.to_dict() == {
        "schema": {
            "title": "Podcast selection",
            "columns": [
                {
                    "key": "title",
                    "type": "str",
                    "nullable": False,
                    "editable": False,
                    "visible": True,
                    "label": "title",
                },
                {
                    "key": "url",
                    "type": "str",
                    "nullable": False,
                    "editable": True,
                    "visible": True,
                    "label": "URL",
                },
                {
                    "key": "publish",
                    "type": "bool",
                    "nullable": False,
                    "editable": False,
                    "visible": False,
                    "label": "publish",
                },
            ],
        },
        "rows": [
            {
                "title": "First",
                "url": "https://example.test/1",
                "publish": True,
            },
            {
                "title": "Second",
                "url": "https://example.test/2",
                "publish": False,
            },
        ],
    }


@pytest.mark.parametrize(
    ("column_type", "expected"),
    [
        (str, "str"),
        ("str", "str"),
        (int, "int"),
        ("int", "int"),
        (float, "float"),
        ("float", "float"),
        (bool, "bool"),
        ("bool", "bool"),
        (date, "date"),
        ("date", "date"),
        (datetime, "datetime"),
        ("datetime", "datetime"),
    ],
)
def test_confirmation_table_accepts_python_and_string_column_types(
    column_type,
    expected,
) -> None:
    table = ConfirmationTable("Review").column("value", column_type, nullable=True)
    table.rows.add([None])

    assert table.to_dict()["schema"]["columns"][0]["type"] == expected


def test_confirmation_table_serializes_python_date_and_datetime_values() -> None:
    table = (
        ConfirmationTable("Dates")
        .column("day", date)
        .column("timestamp", datetime)
    )
    table.rows.add(
        [
            date(2026, 10, 7),
            datetime(2026, 10, 7, 12, 30, 45),
        ]
    )

    assert table.to_dict()["rows"] == [
        {
            "day": "2026-10-07",
            "timestamp": "2026-10-07T12:30:45",
        }
    ]


def test_confirmation_table_accepts_iso_date_and_datetime_values() -> None:
    table = (
        ConfirmationTable("Dates")
        .column("day", "date")
        .column("timestamp", "datetime")
    )
    table.rows.add(["2026-10-07", "2026-10-07T12:30:45Z"])

    assert table.to_dict()["rows"] == [
        {
            "day": "2026-10-07",
            "timestamp": "2026-10-07T12:30:45Z",
        }
    ]


def test_confirmation_table_freezes_columns_after_first_row() -> None:
    table = ConfirmationTable("Review").column("title", str)
    table.rows.add(["First"])

    with pytest.raises(ValueError, match="Cannot add columns"):
        table.column("url", str)


@pytest.mark.parametrize(
    "build",
    [
        lambda: ConfirmationTable("Review").column("value", list),
        lambda: ConfirmationTable("Review").column("avalon_confirmation", str),
        lambda: ConfirmationTable("Review").column("value", str).column("value", str),
    ],
)
def test_confirmation_table_rejects_invalid_columns(build) -> None:
    with pytest.raises(ValueError):
        build()


def test_confirmation_table_rejects_invalid_positional_rows() -> None:
    table = ConfirmationTable("Review").column("title", str).column("count", int)

    with pytest.raises(ValueError, match="Expected 2 row values"):
        table.rows.add(["Only title"])

    with pytest.raises(TypeError, match="'count' must be int"):
        table.rows.add(["Title", True])


def test_confirmation_table_rejects_missing_and_unknown_named_values() -> None:
    table = ConfirmationTable("Review").column("title", str).column("count", int)

    with pytest.raises(ValueError, match="Missing row values: count"):
        table.rows.add(title="Title")

    with pytest.raises(ValueError, match="Unknown row values: extra"):
        table.rows.add(title="Title", count=1, extra=True)


def test_confirmation_table_enforces_nullable() -> None:
    table = ConfirmationTable("Review").column("required", str)

    with pytest.raises(ValueError, match="'required' must not be null"):
        table.rows.add([None])

    nullable = ConfirmationTable("Review").column("optional", str, nullable=True)
    nullable.rows.add([None])

    assert nullable.to_dict()["rows"] == [{"optional": None}]


def test_confirmation_table_requires_columns_and_rows() -> None:
    with pytest.raises(ValueError, match="at least one column"):
        ConfirmationTable("Review").to_dict()

    table = ConfirmationTable("Review").column("title", str)
    with pytest.raises(ValueError, match="at least one row"):
        table.to_dict()


def test_confirmation_table_requires_rows_after_columns_exist() -> None:
    table = ConfirmationTable("Review")

    with pytest.raises(ValueError, match="Add at least one column"):
        table.rows.add(["Title"])


def test_confirmation_table_rejects_mixed_row_forms() -> None:
    table = ConfirmationTable("Review").column("title", str)

    with pytest.raises(ValueError, match="either as a list or as named values"):
        table.rows.add(["Title"], title="Other")