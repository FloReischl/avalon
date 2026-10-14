"""Offline contracts for Gmail inbox-organizer AP4 taxonomy normalization."""

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "workflows"))

from avalon_workflows.inbox_taxonomy_normalizer import InboxTaxonomyNormalizer


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


def test_llm_failure_never_returns_unnormalized_categories() -> None:
    client = FakeClient(["Existing"], [RuntimeError("offline")])

    with pytest.raises(RuntimeError, match="LLM failed"):
        asyncio.run(InboxTaxonomyNormalizer(client).normalize({"one": ["Rechnung"]}))


def test_category_read_failure_aborts_before_the_llm_is_called() -> None:
    client = FakeClient(RuntimeError("mail unavailable"), [])

    with pytest.raises(RuntimeError, match="mail unavailable"):
        asyncio.run(InboxTaxonomyNormalizer(client).normalize({"one": ["Rechnung"]}))
    assert client.prompts == []


def test_large_inputs_are_processed_in_bounded_batches() -> None:
    proposals = {str(index): [f"Kategorie {index:02d}"] for index in range(12)}
    client = FakeClient(
        ["Existing"],
        [
            mapping({f"Kategorie {index:02d}": f"Ziel/{index:02d}" for index in range(5)}),
            mapping({f"Kategorie {index:02d}": f"Ziel/{index:02d}" for index in range(5, 10)}),
            mapping({f"Kategorie {index:02d}": f"Ziel/{index:02d}" for index in range(10, 12)}),
        ],
    )

    result = asyncio.run(
        InboxTaxonomyNormalizer(client, input_budget_chars=700).normalize(proposals)
    )

    assert result == {str(index): [f"Ziel/{index:02d}"] for index in range(12)}
    assert len(client.prompts) > 1
    assert all(len(prompt) <= 700 for prompt in client.prompts)
