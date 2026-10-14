"""Offline data-flow contract connecting AP2, AP3, and AP4."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "workflows"))

from avalon_workflows.inbox_organizer import InboxOrganizer


class Collector:
    def collect(self):
        async def values():
            yield "thread"

        return values()


class Analyzer:
    async def analyze(self, threads):
        assert [thread async for thread in threads] == ["thread"]
        return {"thread": ["Rechnung"]}


class Normalizer:
    async def normalize(self, proposals):
        assert proposals == {"thread": ["Rechnung"]}
        return {"thread": ["Finanzen/Rechnungen"]}


def test_organizer_hands_ap3_proposals_to_ap4_before_the_future_ap5() -> None:
    organizer = InboxOrganizer(Collector(), Analyzer(), Normalizer())

    assert asyncio.run(organizer.analyze()) == {
        "thread": ["Finanzen/Rechnungen"]
    }
