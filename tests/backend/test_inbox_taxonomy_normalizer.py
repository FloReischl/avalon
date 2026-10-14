"""Offline contracts for Gmail inbox-organizer AP4 taxonomy normalization."""

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "workflows"))

from avalon_workflows.inbox_taxonomy_normalizer import (
    InboxTaxonomyNormalizer,
    _normalization_prompt,
)


class FakeClient:
    def __init__(self, categories: object, results: list[object]) -> None:
        self.categories = categories
        self.results = results
        self.prompts: list[str] = []
        self.mutations: list[object] = []

    async def get_mail_categories(self) -> list[str]:
        if isinstance(self.categories, Exception):
            raise self.categories
        return self.categories  # type: ignore[return-value]

    async def llm(self, prompt: str, **_kwargs: object) -> str:
        self.prompts.append(prompt)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        if callable(result):
            return result(prompt)
        return result  # type: ignore[return-value]


def mapping(values: dict[str, str]) -> str:
    return json.dumps({"mapping": values})


def test_normalizes_global_synonyms_with_existing_non_system_categories() -> None:
    client = FakeClient(
        ["INBOX", "[Gmail]/All Mail", "Finanzen/Rechnungen", "Alt"],
        [
            mapping(
                {
                    "Belege": "Finanzen/Rechnungen",
                    "Rechnungen": "Finanzen/Rechnungen",
                    "Urlaub": "Reisen/Urlaub",
                }
            )
        ],
    )
    proposals = {
        "one": ["Jahr/2025", "has-attachments", "Rechnungen", "Belege"],
        "two": ["Urlaub", "Belege"],
    }

    result = asyncio.run(InboxTaxonomyNormalizer(client).normalize(proposals))

    assert result == {
        "one": ["Jahr/2025", "has-attachments", "Finanzen/Rechnungen"],
        "two": ["Reisen/Urlaub", "Finanzen/Rechnungen"],
    }
    prompt = client.prompts[0]
    assert "Finanzen/Rechnungen" in prompt
    assert "INBOX" not in prompt and "[Gmail]/All Mail" not in prompt
    assert '"frequency":2' in prompt
    assert client.mutations == []


def test_category_frequency_counts_threads_not_duplicate_entries() -> None:
    client = FakeClient(
        ["Existing"],
        [mapping({"Rechnung": "Finanzen/Rechnungen"})],
    )

    asyncio.run(
        InboxTaxonomyNormalizer(client).normalize(
            {"one": ["Rechnung", "Rechnung"], "two": ["Rechnung"]}
        )
    )

    assert '"frequency":2' in client.prompts[0]


def test_keeps_technical_and_uncategorized_categories_without_an_llm_call() -> None:
    client = FakeClient(["Project"], [])
    proposals = {"one": ["Jahr/2024", "has-attachments", "Nicht kategorisiert"]}

    assert asyncio.run(InboxTaxonomyNormalizer(client).normalize(proposals)) == proposals
    assert client.prompts == []


@pytest.mark.parametrize(
    "response",
    [
        mapping({"Rechnung": "Finanzen/Rechnungen", "unexpected": "Other"}),
        mapping({"Rechnung": "Jahr/2025"}),
        mapping({"Rechnung": "Finanzen//Rechnungen"}),
        mapping({"Rechnung": "INBOX"}),
    ],
)
def test_retries_and_rejects_invalid_mappings(response: str) -> None:
    client = FakeClient(["Existing"], [response, response])

    with pytest.raises(ValueError, match="invalid taxonomy mapping repeatedly"):
        asyncio.run(InboxTaxonomyNormalizer(client).normalize({"one": ["Rechnung"]}))
    assert len(client.prompts) == 2
    assert "previous_validation_error" in client.prompts[1]


def test_retry_reserves_prompt_space_for_validation_feedback() -> None:
    client = FakeClient(
        ["Existing"],
        ["not json", mapping({"Rechnung": "Finanzen/Rechnungen"})],
    )

    result = asyncio.run(
        InboxTaxonomyNormalizer(client, input_budget_chars=800).normalize(
            {"one": ["Rechnung"]}
        )
    )

    assert result == {"one": ["Finanzen/Rechnungen"]}
    assert len(client.prompts) == 2
    assert all(len(prompt) <= 800 for prompt in client.prompts)


def test_long_validation_error_is_clipped_to_the_reserved_retry_budget() -> None:
    source = "Kategorie-" + "x" * 1_000
    prompt = _normalization_prompt([source], {source: 1}, ["Existing"], None)
    budget = len(prompt) + 256
    client = FakeClient(
        ["Existing"],
        [mapping({source: "INBOX"}), mapping({source: "Finanzen/Rechnungen"})],
    )

    assert asyncio.run(
        InboxTaxonomyNormalizer(client, input_budget_chars=budget).normalize(
            {"one": [source]}
        )
    ) == {"one": ["Finanzen/Rechnungen"]}
    assert all(len(value) <= budget for value in client.prompts)


def test_consolidation_allows_a_rename_round_before_categories_merge() -> None:
    class PlannedNormalizer(InboxTaxonomyNormalizer):
        def __init__(self) -> None:
            super().__init__(FakeClient([], []))
            self.calls = 0

        async def _map_categories(self, frequencies, existing):
            self.calls += 1
            if self.calls == 1:
                return {"A": "C", "B": "D"}, 2
            return {"C": "Finanzen/Rechnungen", "D": "Finanzen/Rechnungen"}, 1

    normalizer = PlannedNormalizer()

    result = asyncio.run(
        normalizer._consolidate_targets(
            {"source-a": "A", "source-b": "B"},
            {"source-a": 1, "source-b": 1},
            [],
        )
    )

    assert result == {"A": "Finanzen/Rechnungen", "B": "Finanzen/Rechnungen"}


def test_llm_failure_never_returns_unnormalized_categories() -> None:
    client = FakeClient(["Existing"], [RuntimeError("offline")])

    with pytest.raises(RuntimeError, match="LLM failed"):
        asyncio.run(InboxTaxonomyNormalizer(client).normalize({"one": ["Rechnung"]}))


def test_category_read_failure_aborts_before_the_llm_is_called() -> None:
    client = FakeClient(RuntimeError("mail unavailable"), [])

    with pytest.raises(RuntimeError, match="mail unavailable"):
        asyncio.run(InboxTaxonomyNormalizer(client).normalize({"one": ["Rechnung"]}))
    assert client.prompts == []


def test_large_inputs_receive_a_global_consolidation_after_local_batches() -> None:
    proposals = {
        str(index): [f"Beleg {index:02d}", f"Rechnung {index:02d}"]
        for index in range(12)
    }

    def response(prompt: str) -> str:
        request = json.loads(prompt.split("\n", 1)[1])
        sources = [item["name"] for item in request["source_categories"]]
        if all(source.startswith("Finanzen/") for source in sources):
            return mapping({source: "Finanzen/Rechnungen" for source in sources})
        return mapping(
            {
                source: (
                    "Finanzen/Belege"
                    if source.startswith("Beleg")
                    else "Finanzen/Rechnungen"
                )
                for source in sources
            }
        )

    client = FakeClient(
        ["Existing"],
        [response] * 20,
    )

    result = asyncio.run(
        InboxTaxonomyNormalizer(client, input_budget_chars=1_000).normalize(proposals)
    )

    assert result == {str(index): ["Finanzen/Rechnungen"] for index in range(12)}
    assert len(client.prompts) > 1
    assert all(len(prompt) <= 1_000 for prompt in client.prompts)
