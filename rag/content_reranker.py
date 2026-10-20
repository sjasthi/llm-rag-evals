
"""Deterministic, content-aware reranking of retrieved evidence."""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from query import SearchResult


INTENT_TERMS = {
    "table": {
        "table", "tabular", "quantity", "quantities",
        "count", "counts", "number", "numbers",
        "limit", "limits", "assigned", "lead", "leads",
        "category", "categories", "turnaround",
        "requirement", "requirements",
    },
    "diagram": {
        "diagram", "flowchart", "workflow", "route",
        "sequence", "steps", "order", "path",
        "process", "transition",
    },
    "image": {
        "image", "photo", "photograph", "picture",
        "screenshot", "shown", "visible",
    },
}

# Keep these weights modest to avoid overpowering retrieval relevance.
TYPE_MATCH_BONUS = 0.12
EVIDENCE_MATCH_BONUS = 0.08


def question_tokens(question: str) -> set[str]:
    """Normalize question words for intent detection."""
    return set(re.findall(r"[a-z0-9]+", question.lower()))


def detect_content_intent(question: str) -> set[str]:
    """Identify evidence types suggested by the question."""
    tokens = question_tokens(question)

    return {
        content_type
        for content_type, terms in INTENT_TERMS.items()
        if tokens.intersection(terms)
    }


def evidence_overlap(question: str, text: str) -> float:
    """Measure overlap of informative question terms and chunk text."""
    stopwords = {
        "a", "an", "and", "are", "as", "at", "by",
        "for", "from", "in", "is", "of", "on",
        "the", "to", "what", "which", "who",
        "with", "according", "listed",
    }

    question_terms = question_tokens(question) - stopwords
    text_terms = question_tokens(text)

    if not question_terms:
        return 0.0

    return len(question_terms & text_terms) / len(question_terms)


def rerank_results(
    question: str,
    candidates: list[SearchResult],
    top_k: int,
) -> list[SearchResult]:
    """Rerank candidates using original order and evidence relevance."""
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")

    intents = detect_content_intent(question)

    scored = []

    for position, candidate in enumerate(candidates, start=1):
        # Reciprocal rank preserves the selected retrieval method's
        # original ordering without comparing incompatible score scales.
        base_score = 1.0 / (1.0 + 0.1 * (position - 1))

        content_type = (candidate.content_type or "").lower()

        type_bonus = (
            TYPE_MATCH_BONUS
            if content_type in intents
            else 0.0
        )

        overlap = evidence_overlap(question, candidate.text)
        evidence_bonus = EVIDENCE_MATCH_BONUS * overlap

        final_score = base_score + type_bonus + evidence_bonus

        scored.append(
            (
                final_score,
                position,
                candidate,
                type_bonus,
                evidence_bonus,
            )
        )

    scored.sort(key=lambda item: (-item[0], item[1]))

    results = []

    for new_rank, (
        score,
        original_rank,
        candidate,
        type_bonus,
        evidence_bonus,
    ) in enumerate(scored[:top_k], start=1):
        results.append(
            type(candidate)(
                **{
                    **asdict(candidate),
                    "rank": new_rank,
                    "retrieval_metadata": {
                        **candidate.retrieval_metadata,
                        "content_reranking": {
                            "enabled": True,
                            "version": "content-aware-v1",
                            "original_rank": original_rank,
                            "rerank_score": score,
                            "type_bonus": type_bonus,
                            "evidence_bonus": evidence_bonus,
                            "detected_intents": sorted(intents),
                        },
                    },
                }
            )
        )

    return results
