"""End-to-end Gmail inbox-organizer workflow orchestration."""

from __future__ import annotations

from typing import Protocol

from .inbox_taxonomy_normalizer import InboxTaxonomyNormalizer
from .inbox_thread_analyzer import InboxThreadAnalyzer
from .inbox_thread_collector import InboxThreadCollector
from .inbox_confirmation import (
    BatchApplication,
    InboxConfirmationClient,
    confirm_and_apply,
    proposals_for_threads,
    thread_batches,
)


class InboxOrganizerClient(InboxConfirmationClient, Protocol):
    async def progress(self, message: str) -> None: ...


class InboxOrganizer:
    """Connect collection, analysis, and AP4 normalization for the later AP5."""

    def __init__(
        self,
        collector: InboxThreadCollector,
        analyzer: InboxThreadAnalyzer,
        normalizer: InboxTaxonomyNormalizer,
        *,
        client: InboxOrganizerClient | None = None,
        batch_size: int = 100,
    ) -> None:
        self._collector = collector
        self._analyzer = analyzer
        self._normalizer = normalizer
        self._client = client
        self._batch_size = batch_size

    async def analyze(self) -> dict[str, list[str]]:
        proposals = await self._analyzer.analyze(self._collector.collect())
        return await self._normalizer.normalize(proposals)

    async def run(self) -> dict[str, int | bool]:
        """Run AP2--AP5 sequentially and return content-free summary statistics."""
        if self._client is None:
            raise RuntimeError("InboxOrganizer.run requires an Avalon workflow client.")
        client = self._client
        await client.progress("Inbox-Erfassung wird gestartet.")
        collected = []

        async def capture():
            async for thread in self._collector.collect():
                collected.append(thread)
                yield thread

        await client.progress("Thread-Analyse wird durchgeführt.")
        proposals = await self._analyzer.analyze(capture())
        await client.progress("Globale Kategorienormalisierung wird durchgeführt.")
        normalized = await self._normalizer.normalize(proposals)
        threads = proposals_for_threads(collected, normalized)
        batches = thread_batches(threads, size=self._batch_size)
        summary = {
            "collected_threads": len(collected),
            "analyzed_threads": len(threads),
            "archived_threads": 0,
            "unchanged_threads": len(collected) - len(threads),
            "failed_threads": 0,
            "cancelled": False,
        }
        if not batches:
            await client.progress("Abschluss: Keine Kategorievorschläge vorhanden.")
            return summary

        for index, batch in enumerate(batches, start=1):
            await client.progress(f"Confirmation-Batch {index} / {len(batches)}.")
            outcome = await confirm_and_apply(
                client, batch, index=index, total=len(batches)
            )
            if outcome is None:
                summary["cancelled"] = True
                summary["unchanged_threads"] += sum(
                    len(remaining) for remaining in batches[index - 1 :]
                )
                await client.progress("Workflow nach Benutzerabbruch kontrolliert beendet.")
                return summary
            await self._apply_outcome(client, outcome, summary)
            await client.progress(
                f"Batch {index} abgeschlossen: {outcome.archived_threads} archiviert, "
                f"{outcome.unchanged_threads} unverändert, {outcome.failed_threads} fehlgeschlagen."
            )

        await client.progress(
            "Abschluss: "
            f"{summary['collected_threads']} erfasst, "
            f"{summary['analyzed_threads']} analysiert, "
            f"{summary['archived_threads']} archiviert, "
            f"{summary['unchanged_threads']} unverändert, "
            f"{summary['failed_threads']} fehlgeschlagen."
        )
        return summary

    @staticmethod
    async def _apply_outcome(
        client: InboxOrganizerClient,
        outcome: BatchApplication,
        summary: dict[str, int | bool],
    ) -> None:
        await client.progress("Bestätigte Kategorien werden angewendet.")
        summary["archived_threads"] = int(summary["archived_threads"]) + outcome.archived_threads
        summary["unchanged_threads"] = int(summary["unchanged_threads"]) + outcome.unchanged_threads
        summary["failed_threads"] = int(summary["failed_threads"]) + outcome.failed_threads
