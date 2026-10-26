
"""Deterministic validation of citations in RAG-generated answers."""

import re
from dataclasses import asdict, dataclass

# Match standalone numeric citations: [1], [2], [12], etc.
# Also supports adjacent citations such as [1][2].
CITATION_PATTERN = re.compile(r"(?<!\w)\[(\d+)\]")

REFUSAL_MESSAGE = (
    "I don't have enough information in the provided Metro State documents "
    "to answer that question."
)


@dataclass(frozen=True)
class CitationValidation:
    citations_found: list[int]
    valid_citations: list[int]
    invalid_citations: list[int]
    available_source_ids: list[int]
    has_citations: bool
    is_refusal: bool
    citation_validity_score: float | None
    citation_presence_passed: bool
    passed: bool

    def to_dict(self) -> dict:
        return asdict(self)


def validate_citations(
    answer_text: str,
    retrieved_sources: list,
) -> CitationValidation:
    """
    Validate numeric source references in a generated answer.

    retrieved_sources may contain SearchResult objects or dictionaries
    with a 'rank' field.

    This checks reference validity and presence, not factual support.
    """
    available_ids = set()

    for source in retrieved_sources:
        if isinstance(source, dict):
            rank = source.get("rank")
        else:
            rank = getattr(source, "rank", None)

        if isinstance(rank, int) and not isinstance(rank, bool) and rank > 0:
            available_ids.add(rank)

    # Preserve citation order while removing duplicate references.
    citations = list(dict.fromkeys(
        int(match) for match in CITATION_PATTERN.findall(answer_text)
    ))

    valid = [number for number in citations if number in available_ids]
    invalid = [number for number in citations if number not in available_ids]

    is_refusal = answer_text.strip() == REFUSAL_MESSAGE
    has_citations = bool(citations)

    # A refusal should not contain citations.
    # A supported answer should contain at least one citation.
    presence_passed = not has_citations if is_refusal else has_citations

    # None means the metric is not applicable because no citations exist.
    validity_score = (
        len(valid) / len(citations)
        if citations
        else None
    )

    passed = presence_passed and not invalid

    return CitationValidation(
        citations_found=citations,
        valid_citations=valid,
        invalid_citations=invalid,
        available_source_ids=sorted(available_ids),
        has_citations=has_citations,
        is_refusal=is_refusal,
        citation_validity_score=validity_score,
        citation_presence_passed=presence_passed,
        passed=passed,
    )
