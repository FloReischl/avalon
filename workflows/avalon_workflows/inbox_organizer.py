"""Content-bounded AP2--AP4 inbox-organizer data flow."""

from __future__ import annotations

from .inbox_taxonomy_normalizer import InboxTaxonomyNormalizer
from .inbox_thread_analyzer import InboxThreadAnalyzer
from .inbox_thread_collector import InboxThreadCollector


class InboxOrganizer:
    """Connect collection, analysis, and AP4 normalization for the later AP5."""

    def __init__(
        self,
        collector: InboxThreadCollector,
        analyzer: InboxThreadAnalyzer,
        normalizer: InboxTaxonomyNormalizer,
    ) -> None:
        self._collector = collector
        self._analyzer = analyzer
        self._normalizer = normalizer

    async def analyze(self) -> dict[str, list[str]]:
        proposals = await self._analyzer.analyze(self._collector.collect())
        return await self._normalizer.normalize(proposals)
