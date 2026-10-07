"""Simple workflow for manually testing ConfirmationTable."""

import asyncio
import json
from datetime import date
from pathlib import Path

from avalon_workflows import AvalonWorkflowClient, ConfirmationTable


OUTPUT_FILE = Path("/tmp/avalon/confirmation-test.json")


async def main() -> None:
    client = AvalonWorkflowClient.from_stdin()

    table = (
        ConfirmationTable("Confirmation Test")
        .column("name", str, label="Name")
        .column("count", int, label="Count")
        .column("date", date, label="Date")
    )

    table.rows \
        .add(["Alpha", 1, date(2026, 10, 7)]) \
        .add(["Beta", 2, date(2026, 10, 8)]) \
        .add(["Gamma", 3, date(2026, 10, 9)])

    result = await client.confirm(table)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    asyncio.run(main())