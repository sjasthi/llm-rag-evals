
"""Deterministic scoring for factual-claim citation coverage."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from citation_support import AnswerStatement

class CitationCoverageClaim(BaseModel):
    statement_id: int = Field(ge=1)
    claim: str = Field(min_length=1)
    citation_ids: list[int] = Field(default_factory=list)

class CitationCoverageOutput(BaseModel):
    claims: list[CitationCoverageClaim]
    summary: str = ""
    reviewed_statement_ids: list[int] = Field(default_factory=list)

def validate_coverage_statement_completeness(
    output: CitationCoverageOutput,
    statement_count: int,
) -> dict:
    """Verify that every answer statement was explicitly reviewed."""
    if statement_count < 1:
        raise ValueError("Statement count must be positive.")

    expected_ids = set(range(1, statement_count + 1))
    reviewed_ids = output.reviewed_statement_ids

    if len(reviewed_ids) != len(set(reviewed_ids)):
        raise ValueError("Duplicate reviewed statement IDs were returned.")

    actual_ids = set(reviewed_ids)

    missing_ids = expected_ids - actual_ids
    unexpected_ids = actual_ids - expected_ids

    if missing_ids or unexpected_ids:
        raise ValueError(
            "Citation Coverage statement review is incomplete. "
            f"Missing IDs: {sorted(missing_ids)}; "
            f"unexpected IDs: {sorted(unexpected_ids)}."
        )

    claim_statement_ids = {
        claim.statement_id for claim in output.claims
    }

    if not claim_statement_ids.issubset(actual_ids):
        raise ValueError(
            "Citation Coverage contains claims from unreviewed statements."
        )

    return {
        "total_statements": statement_count,
        "reviewed_statements": len(actual_ids),
        "statement_review_coverage": 1.0,
    }

def score_citation_coverage(
    output: CitationCoverageOutput,
    evidence_by_rank: dict[int, str],
) -> dict:
    """Calculate the fraction of factual claims with valid citations.

    A claim is covered if it has at least one citation referring to
    nonempty saved evidence. This does not establish factual support.
    """
    valid_ids = {
        rank
        for rank, evidence in evidence_by_rank.items()
        if evidence and evidence.strip()
    }

    claim_results = []

    for claim in output.claims:
        valid_citations = sorted(
            set(claim.citation_ids) & valid_ids
        )
        invalid_citations = sorted(
            set(claim.citation_ids) - valid_ids
        )

        claim_results.append({
            "statement_id": claim.statement_id,
            "claim": claim.claim,
            "citation_ids": claim.citation_ids,
            "valid_citation_ids": valid_citations,
            "invalid_citation_ids": invalid_citations,
            "covered": bool(valid_citations),
        })

    total_claims = len(claim_results)
    covered_claims = sum(
        1 for claim in claim_results if claim["covered"]
    )

    return {
        "score": (
            covered_claims / total_claims
            if total_claims else None
        ),
        "total_claims": total_claims,
        "covered_claims": covered_claims,
        "uncovered_claims": total_claims - covered_claims,
        "claims": claim_results,
    }

def validate_coverage_claim_references(
    output: CitationCoverageOutput,
    statements: list[AnswerStatement],
) -> None:
    """Ensure claim citations match their originating answer statement.

    Statement IDs are 1-based positions in the extracted statement list.
    Gemini may identify factual claims, but it cannot introduce citations
    that were not present in the original statement.
    """
    statement_lookup = {
        index: statement
        for index, statement in enumerate(statements, start=1)
    }

    for claim in output.claims:
        statement = statement_lookup.get(claim.statement_id)

        if statement is None:
            raise ValueError(
                f"Claim references unknown statement_id "
                f"{claim.statement_id}."
            )

        original_citations = set(statement.citation_ids)
        claimed_citations = set(claim.citation_ids)

        unexpected_citations = claimed_citations - original_citations

        if unexpected_citations:
            raise ValueError(
                f"Claim for statement {claim.statement_id} "
                f"references citations not present in the original "
                f"statement: {sorted(unexpected_citations)}"
            )

def normalize_coverage_claim_citations(
    output: CitationCoverageOutput,
    statements: list[AnswerStatement],
) -> CitationCoverageOutput:
    """Assign citations from the original answer to extracted claims.

    The model identifies factual claims and their statement IDs.
    Python is authoritative for citation references.
    """
    validate_coverage_claim_references(output, statements)

    statement_lookup = {
        index: statement
        for index, statement in enumerate(statements, start=1)
    }

    normalized_claims = []

    for claim in output.claims:
        statement = statement_lookup[claim.statement_id]

        normalized_claims.append(
            CitationCoverageClaim(
                statement_id=claim.statement_id,
                claim=claim.claim,
                citation_ids=list(statement.citation_ids),
            )
        )

    return CitationCoverageOutput(
        claims=normalized_claims,
        summary=output.summary,
    )
