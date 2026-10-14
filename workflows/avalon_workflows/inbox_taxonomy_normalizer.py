"""Global, content-free normalization of inbox-organizer category proposals."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from typing import Protocol


DEFAULT_INPUT_BUDGET_CHARS = 8_000 * 3
_LLM_ATTEMPTS = 2
_UNCATEGORIZED = "Nicht kategorisiert"


class TaxonomyNormalizationClient(Protocol):
    """The deliberately small AP4 client surface."""

    async def get_mail_categories(self) -> list[str]: ...

    async def llm(self, prompt: str, **kwargs: object) -> str: ...


class InboxTaxonomyNormalizer:
    """Normalize proposals using only category names and their frequencies.

    The component neither loads mail content nor exposes any mail mutation.  A
    caller can therefore run it between AP3 and AP5 without retaining analysis
    evidence beyond the compact proposal mapping.
    """

    def __init__(
        self,
        client: TaxonomyNormalizationClient,
        *,
        input_budget_chars: int = DEFAULT_INPUT_BUDGET_CHARS,
    ) -> None:
        if input_budget_chars < 256:
            raise ValueError("input_budget_chars must be at least 256.")
        self._client = client
        self._input_budget_chars = input_budget_chars

    async def normalize(self, proposals: Mapping[str, list[str]]) -> dict[str, list[str]]:
        """Return proposals with globally normalized, non-technical categories."""
        existing = await self._existing_categories()
        frequencies = _category_frequencies(proposals)
        if not frequencies:
            return _copy_proposals(proposals)

        mapping: dict[str, str] = {}
        for sources in _batches(
            frequencies, existing, self._input_budget_chars
        ):
            mapping.update(await self._normalize_batch(sources, frequencies, existing))
        # This guards batching mistakes as well as an LLM response that happened
        # to be individually valid but did not cover the global input.
        if set(mapping) != set(frequencies):
            raise ValueError("Taxonomy normalization did not map every source category.")
        return _rewrite_proposals(proposals, mapping)

    async def _existing_categories(self) -> list[str]:
        values = await self._client.get_mail_categories()
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ValueError("Mail capability returned invalid categories.")
        return sorted(
            {
                value.strip()
                for value in values
                if value.strip() and not _is_system_category(value.strip())
            }
        )

    async def _normalize_batch(
        self,
        sources: list[str],
        frequencies: Counter[str],
        existing: list[str],
    ) -> dict[str, str]:
        feedback: str | None = None
        for attempt in range(_LLM_ATTEMPTS):
            prompt = _normalization_prompt(sources, frequencies, existing, feedback)
            if len(prompt) > self._input_budget_chars:
                raise ValueError("Taxonomy normalization prompt exceeds its input budget.")
            try:
                response = await self._client.llm(
                    prompt,
                    persona=None,
                    context=None,
                    instructions=(
                        "Antworte ausschließlich mit dem verlangten JSON. "
                        "Jede Quellkategorie muss genau einmal zugeordnet sein."
                    ),
                )
            except Exception as exc:
                raise RuntimeError("LLM failed during taxonomy normalization.") from exc
            try:
                return _validate_mapping(response, sources)
            except ValueError as exc:
                feedback = str(exc)
                if attempt + 1 == _LLM_ATTEMPTS:
                    raise ValueError(
                        "LLM returned an invalid taxonomy mapping repeatedly."
                    ) from exc
        raise AssertionError("unreachable")


def _category_frequencies(proposals: Mapping[str, list[str]]) -> Counter[str]:
    frequencies: Counter[str] = Counter()
    for thread_id, categories in proposals.items():
        if not isinstance(thread_id, str) or not thread_id:
            raise ValueError("Proposal has no valid thread ID.")
        if not isinstance(categories, list) or not all(isinstance(value, str) for value in categories):
            raise ValueError("Proposal categories must be lists of strings.")
        for category in categories:
            value = category.strip()
            if not value:
                raise ValueError("Proposal contains an empty category.")
            if not _is_technical_category(value) and value != _UNCATEGORIZED:
                frequencies[value] += 1
    return frequencies


def _batches(
    frequencies: Counter[str], existing: list[str], budget: int
) -> list[list[str]]:
    """Split sources deterministically without silently dropping an input name."""
    sources = sorted(frequencies)
    batches: list[list[str]] = []
    current: list[str] = []
    for source in sources:
        candidate = [*current, source]
        if len(_normalization_prompt(candidate, frequencies, existing, None)) <= budget:
            current = candidate
            continue
        if not current:
            raise ValueError(
                "Taxonomy normalization input budget is too small for one category."
            )
        batches.append(current)
        current = [source]
        if len(_normalization_prompt(current, frequencies, existing, None)) > budget:
            raise ValueError(
                "Taxonomy normalization input budget is too small for one category."
            )
    if current:
        batches.append(current)
    return batches


def _normalization_prompt(
    sources: list[str],
    frequencies: Counter[str],
    existing: list[str],
    feedback: str | None,
) -> str:
    request: dict[str, object] = {
        "source_categories": [
            {"name": source, "frequency": frequencies[source]} for source in sources
        ],
        "existing_gmail_categories": existing,
        "required_response": {"mapping": {"source category": "target/category"}},
        "rules": [
            "Map every source category exactly once and no other source.",
            "Prefer a fitting existing Gmail category.",
            "Use compact semantic categories; separate hierarchy segments with '/'.",
            "Do not use Gmail system labels or technical categories as targets.",
        ],
    }
    if feedback:
        request["previous_validation_error"] = feedback
    return (
        "Normalisiere diese Gmail-Kategorievorschläge zu einer konsistenten Taxonomie. "
        "Gib nur das verlangte JSON zurück.\n"
        + json.dumps(request, ensure_ascii=False, separators=(",", ":"))
    )


def _validate_mapping(response: object, sources: list[str]) -> dict[str, str]:
    if not isinstance(response, str):
        raise ValueError("LLM response is not text.")
    try:
        payload = json.loads(response)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM response is not valid JSON.") from exc
    if not isinstance(payload, dict) or set(payload) != {"mapping"}:
        raise ValueError("LLM response must contain only a mapping object.")
    mapping = payload["mapping"]
    if not isinstance(mapping, dict) or not all(
        isinstance(source, str) and isinstance(target, str)
        for source, target in mapping.items()
    ):
        raise ValueError("LLM mapping must contain string sources and targets.")
    if set(mapping) != set(sources):
        raise ValueError(
            "LLM mapping sources must exactly match the requested categories."
        )
    normalized: dict[str, str] = {}
    for source in sources:
        target = mapping[source].strip()
        if not _is_valid_target(target):
            raise ValueError(f"LLM mapping has an invalid target for {source!r}.")
        normalized[source] = target
    return normalized


def _rewrite_proposals(
    proposals: Mapping[str, list[str]], mapping: Mapping[str, str]
) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}
    for thread_id, categories in proposals.items():
        values: list[str] = []
        seen: set[str] = set()
        for category in categories:
            value = category.strip()
            target = (
                value
                if _is_technical_category(value) or value == _UNCATEGORIZED
                else mapping[value]
            )
            if target not in seen:
                values.append(target)
                seen.add(target)
        normalized[thread_id] = values
    return normalized


def _copy_proposals(proposals: Mapping[str, list[str]]) -> dict[str, list[str]]:
    # Validate even when no LLM call is necessary.
    _category_frequencies(proposals)
    return {thread_id: list(categories) for thread_id, categories in proposals.items()}


def _is_technical_category(value: str) -> bool:
    return value == "has-attachments" or (
        value.startswith("Jahr/") and value[5:].isdigit() and len(value) == 9
    )


def _is_system_category(value: str) -> bool:
    """Recognize labels Gmail reserves and therefore must never be targets."""
    upper = value.upper()
    return upper in {
        "INBOX",
        "SENT",
        "DRAFT",
        "DRAFTS",
        "SPAM",
        "TRASH",
        "STARRED",
        "IMPORTANT",
        "ALL MAIL",
    } or value.startswith(("[Gmail]/", "[Google Mail]/"))


def _is_valid_target(value: str) -> bool:
    return (
        bool(value)
        and all(segment.strip() for segment in value.split("/"))
        and not _is_technical_category(value)
        and value != _UNCATEGORIZED
        and not _is_system_category(value)
    )
