
"""Local preparation of citation-specific evidence for support evaluation."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from citation_validator import CITATION_PATTERN

@dataclass(frozen=True)
class CitedStatement:
    statement: str
    citation_ids: list[int]
    evidence: dict[int, str]
    missing_citation_ids: list[int]

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass(frozen=True)
class AnswerStatement:
    statement: str
    citation_ids: list[int]
    evidence: dict[int, str]
    missing_citation_ids: list[int]

    @property
    def has_citation(self) -> bool:
        return bool(self.citation_ids)

    @property
    def has_valid_citation(self) -> bool:
        return bool(self.evidence)

    def to_dict(self) -> dict:
        return asdict(self)

def extract_answer_statements(
    answer: str,
    evidence_by_rank: dict[int, str],
) -> list[AnswerStatement]:
    """Extract cited and uncited statements with citation metadata.

    This performs structural parsing only. It does not determine whether
    statements contain factual claims or whether evidence supports them.
    """
    if not answer.strip():
        return []

    segments = re.split(r"(?<=[.!?])\s+", answer.strip())
    statements = []

    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue

        citation_ids = list(
            dict.fromkeys(
                int(match)
                for match in CITATION_PATTERN.findall(segment)
            )
        )

        matched_evidence = {
            citation_id: evidence_by_rank[citation_id]
            for citation_id in citation_ids
            if citation_id in evidence_by_rank
        }

        missing_ids = [
            citation_id
            for citation_id in citation_ids
            if citation_id not in evidence_by_rank
        ]

        statements.append(
            AnswerStatement(
                statement=segment,
                citation_ids=citation_ids,
                evidence=matched_evidence,
                missing_citation_ids=missing_ids,
            )
        )

    return statements

def extract_cited_statements(
    answer: str,
    evidence_by_rank: dict[int, str],
) -> list[CitedStatement]:
    """Associate citation-bearing statements with their saved evidence.

    A statement may contain multiple factual claims. This function performs
    structural matching only; it does not determine factual support.
    """
    return [
        CitedStatement(
            statement=item.statement,
            citation_ids=item.citation_ids,
            evidence=item.evidence,
            missing_citation_ids=item.missing_citation_ids,
        )
        for item in extract_answer_statements(answer, evidence_by_rank)
        if item.has_citation
    ]
