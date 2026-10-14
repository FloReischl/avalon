"""Run the Gmail inbox organizer through Avalon workflow capabilities."""

from __future__ import annotations

import asyncio

from avalon_workflows import (
    AvalonWorkflowClient,
    InboxOrganizer,
    InboxTaxonomyNormalizer,
    InboxThreadAnalyzer,
    InboxThreadCollector,
)


async def main() -> None:
    client = AvalonWorkflowClient.from_stdin()
    organizer = InboxOrganizer(
        InboxThreadCollector(client),
        InboxThreadAnalyzer(client),
        InboxTaxonomyNormalizer(client),
        client=client,
    )
    result = await organizer.run()
    client.log(
        "Inbox organizer finished: "
        f"{result['archived_threads']} archived, {result['failed_threads']} failed."
    )


if __name__ == "__main__":
    asyncio.run(main())
