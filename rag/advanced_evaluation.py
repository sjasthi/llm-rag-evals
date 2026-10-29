"""FP8 LLM-judge and RAGAS evaluators for already-saved RAG responses."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from ragas.llms.base import InstructorBaseRagasLLM

from evaluation import EvaluationInput, EvaluationResult, normalize_text
from evaluator_catalog import ADVANCED_DEFINITIONS, definition_for
from llm import REFUSAL_MESSAGE
from settings import Settings
from citation_support import (
    extract_answer_statements,
    extract_cited_statements,
)
from citation_coverage import (
    CitationCoverageOutput,
    normalize_coverage_claim_citations,
    score_citation_coverage,
    validate_coverage_statement_completeness,
)

ADVANCED_EVALUATOR_KEYS = [definition["key"] for definition in ADVANCED_DEFINITIONS]
JUDGE_RUBRIC_VERSION = "1.0"

class RubricDimension(BaseModel):
    score: int | None = Field(default=None, ge=0, le=4)
    reason: str

class JudgeRubricOutput(BaseModel):
    correctness: RubricDimension
    completeness: RubricDimension
    faithfulness: RubricDimension
    relevance: RubricDimension
    answerability: RubricDimension
    overall_decision: Literal["acceptable", "needs_revision", "incorrect"]
    unsupported_claims: list[str] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list)
    summary: str

class CitationSupportClaim(BaseModel):
    statement_id: int
    claim: str
    citation_ids: list[int]
    verdict: Literal[
        "supported",
        "contradicted",
        "insufficient_evidence",
        "unassessable",
    ]
    explanation: str

class CitationSupportOutput(BaseModel):
    claims: list[CitationSupportClaim]
    summary: str

@dataclass(frozen=True)
class ProviderExecution:
    parsed: JudgeRubricOutput | CitationSupportOutput | CitationCoverageOutput
    raw_output: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    thinking_tokens: int | None = None
    finish_reason: str | None = None

@dataclass(frozen=True)
class AdvancedExecution:
    result: EvaluationResult
    raw_provider_output: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    thinking_tokens: int | None = None

JudgeProvider = Callable[[str, Settings], ProviderExecution]
RagasFactory = Callable[[Settings], tuple[dict[str, Any], Any | None]]

class AsyncCompatibleRagasLLM(InstructorBaseRagasLLM):
    """Expose RAGAS' async contract over a synchronous structured-output LLM.

    RAGAS 0.4.3's collection metrics call ``agenerate`` even when their public
    ``score`` method is used. Its Google GenAI factory currently returns a
    synchronous Instructor client, so the unadapted object raises before any
    metric can run. Moving the synchronous generation into a worker thread
    satisfies the async metric pipeline without changing providers or SDKs.
    """

    def __init__(self, delegate: Any) -> None:
        self._delegate = delegate

    def generate(self, prompt: str, response_model: Any) -> Any:
        return self._delegate.generate(prompt, response_model)

    async def agenerate(self, prompt: str, response_model: Any) -> Any:
        return await asyncio.to_thread(
            self._delegate.generate,
            prompt,
            response_model,
        )

def build_judge_prompt(item: EvaluationInput) -> str:
    contexts = "\n\n".join(
        f"[Retrieved context {index}]\n{context}"
        for index, context in enumerate(item.retrieved_contexts, start=1)
    ) or "[No retrieved contexts were saved]"
    required_facts = json.dumps(item.required_facts, ensure_ascii=False)
    return f"""
You are evaluating one saved Metro State RAG response. Use only the reviewed
reference data and retrieved contexts below. Do not answer the original question.
Score each applicable dimension from 0 to 4:

0 = wholly unacceptable or contradicted
1 = major problems
2 = mixed/partial quality
3 = good with a minor issue
4 = fully satisfies the dimension

Use null only when a dimension is genuinely not applicable. For an
unanswerable question, prioritize answerability/refusal behavior; faithfulness
may be null for a claim-free refusal. A high relevance score does not excuse
incorrect or unsupported facts. Return concise, evidence-specific reasons.

Rubric version: {JUDGE_RUBRIC_VERSION}
Question: {item.question}
Reviewed answerability: {"answerable" if item.is_answerable else "unanswerable"}
Reviewed reference answer: {item.expected_answer}
Reviewed expected evidence: {item.expected_evidence or "None"}
Reviewed required facts: {required_facts}
Generated response: {item.actual_answer}

Saved retrieved contexts:
{contexts}
""".strip()

def score_citation_support(
    output: CitationSupportOutput,
    valid_citation_ids: set[int],
    evidence_by_rank: dict[int, str] | None = None,
) -> dict:
    """Validate citation references and score claim-level support."""

    if not output.claims:
        raise ValueError(
            "Citation Support returned no claims to evaluate."
        )

    verdicts = {
        "supported",
        "contradicted",
        "insufficient_evidence",
        "unassessable",
    }

    counts = {verdict: 0 for verdict in verdicts}

    for claim in output.claims:
        if not claim.claim.strip():
            raise ValueError("Citation Support returned an empty claim.")

        if not claim.citation_ids:
            raise ValueError(
                f"Claim has no citation IDs: {claim.claim!r}"
            )

        unknown_ids = set(claim.citation_ids) - valid_citation_ids

        if unknown_ids:
            raise ValueError(
                "Citation Support returned unknown citation IDs: "
                f"{sorted(unknown_ids)}"
            )

        if evidence_by_rank is not None and claim.verdict == "supported":
            missing_evidence = [
                citation_id
                for citation_id in claim.citation_ids
                if not evidence_by_rank.get(citation_id, "").strip()
            ]

            if missing_evidence:
                raise ValueError(
                    "Citation Support marked a claim as supported "
                    "without saved evidence for citation IDs: "
                    f"{missing_evidence}"
                )

        if claim.verdict not in verdicts:
            raise ValueError(
                f"Invalid Citation Support verdict: {claim.verdict}"
            )

        counts[claim.verdict] += 1

    total_claims = len(output.claims)

    assessable_claims = (
        counts["supported"]
        + counts["contradicted"]
        + counts["insufficient_evidence"]
    )

    if assessable_claims == 0:
        score = None
    else:
        score = counts["supported"] / assessable_claims

    coverage = assessable_claims / total_claims

    return {
        "score": score,
        "coverage": coverage,
        "total_claims": total_claims,
        "assessable_claims": assessable_claims,
        "verdict_counts": counts,
    }

def validate_citation_statement_coverage(
    output: CitationSupportOutput,
    expected_statement_ids: set[int],
) -> dict:
    """Ensure every citation-bearing statement is represented."""

    if not expected_statement_ids:
        raise ValueError(
            "Citation Support requires at least one input statement."
        )

    returned_statement_ids = {
        claim.statement_id
        for claim in output.claims
    }

    unknown_ids = returned_statement_ids - expected_statement_ids

    if unknown_ids:
        raise ValueError(
            "Citation Support returned unknown statement IDs: "
            f"{sorted(unknown_ids)}"
        )

    missing_ids = expected_statement_ids - returned_statement_ids

    if missing_ids:
        raise ValueError(
            "Citation Support omitted statements: "
            f"{sorted(missing_ids)}"
        )

    return {
        "total_statements": len(expected_statement_ids),
        "covered_statements": len(returned_statement_ids),
        "statement_coverage": 1.0,
    }

def validate_citation_claim_references(
    output: CitationSupportOutput,
    statements: list,
) -> None:
    """Ensure claims use only citations from their originating statement."""

    statement_citations = {
        index: set(statement.citation_ids)
        for index, statement in enumerate(statements, start=1)
    }

    for claim in output.claims:
        if claim.statement_id not in statement_citations:
            raise ValueError(
                "Citation Support returned an unknown statement ID: "
                f"{claim.statement_id}"
            )

        allowed_ids = statement_citations[claim.statement_id]

        if not claim.citation_ids:
            raise ValueError(
                f"Claim has no citation IDs: {claim.claim!r}"
            )

        invalid_ids = set(claim.citation_ids) - allowed_ids

        if invalid_ids:
            raise ValueError(
                f"Claim from statement {claim.statement_id} "
                f"references citations not present in that statement: "
                f"{sorted(invalid_ids)}"
            )

def build_citation_support_prompt(item: EvaluationInput) -> str:
    """Build a source-specific, claim-level citation support prompt."""

    statements = extract_cited_statements(
        item.actual_answer,
        item.retrieved_evidence_by_rank,
    )

    if not statements:
        raise ValueError(
            "Citation Support requires at least one citation-bearing statement."
        )

    statement_payload = [
        {
            "statement_id": index,
            **statement.to_dict(),
        }
        for index, statement in enumerate(statements, start=1)
    ]

    return f"""
You are evaluating citation support in a saved Metro State RAG response.

Your task is to determine whether each factual claim is supported by
the specific retrieved evidence cited in the generated answer.

Do not answer the user's original question.
Do not use outside knowledge.
Do not use evidence from uncited sources.
Do not assume a citation is correct simply because its ID exists.

For each citation-bearing statement:

1. Identify every independently verifiable factual claim.
2. Separate compound statements into individual factual claims.
3. Preserve the citation IDs associated with each claim.
4. Compare each claim only against its associated cited evidence.
5. Classify each claim using exactly one verdict:

   supported:
     The cited evidence directly supports the claim or clearly
     entails it.

   contradicted:
     The cited evidence explicitly conflicts with the claim.

   insufficient_evidence:
     The cited evidence does not establish the claim.

   unassessable:
     The claim cannot be reliably assessed because essential
     information is unavailable or unreadable.

6. Provide a concise explanation grounded in the cited evidence.

Additional rules:

- Do not invent citation IDs.
- If a citation ID has no matching saved evidence, do not mark
  its claim as supported.
- Do not mark a claim supported based only on general plausibility.
- Numerical values, dates, deadlines, and responsible offices must
  match the cited evidence.
- Paraphrasing is acceptable when the meaning is preserved.
- A source may support one claim while contradicting another.
- Evaluate every factual claim in the supplied statements.
- Return structured output matching the requested schema.

Original question:
{item.question}

Generated answer:
{item.actual_answer}

Citation-bearing statements and their specific saved evidence:
{json.dumps(statement_payload, ensure_ascii=False, indent=2)}
""".strip()

def build_citation_coverage_prompt(item: EvaluationInput) -> str:
    """Build a prompt for extracting factual claims from all statements."""
    statements = extract_answer_statements(
        item.actual_answer,
        item.retrieved_evidence_by_rank,
    )

    if not statements:
        raise ValueError(
            "Citation Coverage requires a nonempty generated answer."
        )

    statement_payload = [
        {
            "statement_id": index,
            "statement": statement.statement,
        }
        for index, statement in enumerate(statements, start=1)
    ]

    return f"""
You are extracting factual claims from a saved Metro State RAG response.

Your task is to identify every independently verifiable factual claim
in the generated answer, including claims without citations.

Do not answer the original question.
Do not evaluate whether claims are true or supported.
Do not use outside knowledge.
Do not invent factual claims.

For each supplied statement:

1. Identify every independently verifiable factual claim.
2. Separate compound statements into individual atomic claims.
3. Preserve the statement_id of the originating statement.
4. Include factual claims from both cited and uncited statements.
5. Do not treat citation markers themselves as factual claims.
6. Do not include purely conversational text, greetings, or
   statements without independently verifiable factual content.
7. If a statement contains no factual claims, return no claims
   for that statement.
8. Do not omit factual claims simply because they lack citations.

Citation handling:

- Return an empty citation_ids list for every extracted claim.
- Python will assign citations from the original answer.
- Do not infer, invent, or assign citation references.

For statement completeness:

- Return reviewed_statement_ids containing every statement_id supplied.
- Include a statement_id even when that statement contains no factual claims.
- Do not include statement IDs that were not supplied.
- Each statement_id must appear exactly once in reviewed_statement_ids.
- Claims must reference their originating statement_id.

Return structured output matching the requested schema.

Original question:
{item.question}

Generated answer:
{item.actual_answer}

Numbered answer statements:
{json.dumps(statement_payload, ensure_ascii=False, indent=2)}
""".strip()

def judge_prompt_hash() -> str:
    template_marker = (
        "metrostate-judge|rubric-1.0|0-4|correctness|completeness|"
        "faithfulness|relevance|answerability"
    )
    return hashlib.sha256(template_marker.encode("utf-8")).hexdigest()

def generate_judge_with_gemini(prompt: str, settings: Settings) -> ProviderExecution:
    if settings.evaluator_provider != "gemini":
        raise ValueError(
            f"Unsupported EVALUATOR_PROVIDER {settings.evaluator_provider!r}; use 'gemini'."
        )
    if not settings.llm_api_key:
        raise RuntimeError("Evaluator API key is not configured.")

    client = genai.Client(api_key=settings.llm_api_key)
    try:
        response = client.models.generate_content(
            model=settings.evaluator_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=settings.evaluator_temperature,
                max_output_tokens=2048,
                response_mime_type="application/json",
                response_schema=JudgeRubricOutput,
            ),
        )
    finally:
        client.close()

    candidate = response.candidates[0] if response.candidates else None
    raw_finish_reason = getattr(candidate, "finish_reason", None)
    finish_reason = (
        getattr(raw_finish_reason, "name", None)
        or (str(raw_finish_reason) if raw_finish_reason is not None else None)
    )
    normalized_finish_reason = (finish_reason or "").upper().split(".")[-1]
    if normalized_finish_reason and normalized_finish_reason not in {
        "STOP",
        "FINISH_REASON_UNSPECIFIED",
    }:
        raise RuntimeError(
            "The evaluator model stopped before a complete rubric "
            f"(finish_reason={finish_reason})."
        )

    raw_output = (response.text or "").strip()
    if not raw_output:
        raise RuntimeError("The evaluator model returned an empty response.")
    parsed_value = response.parsed
    if isinstance(parsed_value, JudgeRubricOutput):
        parsed = parsed_value
    elif parsed_value is not None:
        parsed = JudgeRubricOutput.model_validate(parsed_value)
    else:
        parsed = JudgeRubricOutput.model_validate_json(raw_output)

    usage = response.usage_metadata
    return ProviderExecution(
        parsed=parsed,
        raw_output=raw_output,
        input_tokens=getattr(usage, "prompt_token_count", None),
        output_tokens=getattr(usage, "candidates_token_count", None),
        total_tokens=getattr(usage, "total_token_count", None),
        thinking_tokens=getattr(usage, "thoughts_token_count", None),
        finish_reason=finish_reason,
    )

def generate_citation_support_with_gemini(
    prompt: str,
    settings: Settings,
) -> ProviderExecution:
    """Generate a structured claim-level citation support assessment."""

    if settings.evaluator_provider != "gemini":
        raise ValueError(
            f"Unsupported EVALUATOR_PROVIDER "
            f"{settings.evaluator_provider!r}; use 'gemini'."
        )

    if not settings.llm_api_key:
        raise RuntimeError("Evaluator API key is not configured.")

    client = genai.Client(api_key=settings.llm_api_key)

    try:
        response = client.models.generate_content(
            model=settings.evaluator_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=settings.evaluator_temperature,
                max_output_tokens=4096,
                response_mime_type="application/json",
                response_schema=CitationSupportOutput,
            ),
        )
    finally:
        client.close()

    candidate = response.candidates[0] if response.candidates else None
    raw_finish_reason = getattr(candidate, "finish_reason", None)

    finish_reason = (
        getattr(raw_finish_reason, "name", None)
        or (
            str(raw_finish_reason)
            if raw_finish_reason is not None
            else None
        )
    )

    normalized_finish_reason = (
        (finish_reason or "").upper().split(".")[-1]
    )

    if normalized_finish_reason and normalized_finish_reason not in {
        "STOP",
        "FINISH_REASON_UNSPECIFIED",
    }:
        raise RuntimeError(
            "The citation support model stopped before completing "
            f"its assessment (finish_reason={finish_reason})."
        )

    raw_output = (response.text or "").strip()

    if not raw_output:
        raise RuntimeError(
            "The citation support model returned an empty response."
        )

    parsed_value = response.parsed

    if isinstance(parsed_value, CitationSupportOutput):
        parsed = parsed_value
    elif parsed_value is not None:
        parsed = CitationSupportOutput.model_validate(parsed_value)
    else:
        parsed = CitationSupportOutput.model_validate_json(raw_output)

    usage = response.usage_metadata

    return ProviderExecution(
        parsed=parsed,
        raw_output=raw_output,
        input_tokens=getattr(usage, "prompt_token_count", None),
        output_tokens=getattr(usage, "candidates_token_count", None),
        total_tokens=getattr(usage, "total_token_count", None),
        thinking_tokens=getattr(usage, "thoughts_token_count", None),
        finish_reason=finish_reason,
    )

def generate_citation_coverage_with_gemini(
    prompt: str,
    settings: Settings,
) -> ProviderExecution:
    """Extract factual claims using Gemini structured JSON output."""

    if settings.evaluator_provider != "gemini":
        raise ValueError(
            f"Unsupported EVALUATOR_PROVIDER "
            f"{settings.evaluator_provider!r}; use 'gemini'."
        )

    if not settings.llm_api_key:
        raise RuntimeError("Evaluator API key is not configured.")

    client = genai.Client(api_key=settings.llm_api_key)

    try:
        response = client.models.generate_content(
            model=settings.evaluator_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=settings.evaluator_temperature,
                max_output_tokens=4096,
                response_mime_type="application/json",
                response_schema=CitationCoverageOutput,
            ),
        )
    finally:
        client.close()

    candidate = response.candidates[0] if response.candidates else None
    raw_finish_reason = getattr(candidate, "finish_reason", None)

    finish_reason = (
        getattr(raw_finish_reason, "name", None)
        or (
            str(raw_finish_reason)
            if raw_finish_reason is not None
            else None
        )
    )

    normalized_finish_reason = (
        (finish_reason or "").upper().split(".")[-1]
    )

    if normalized_finish_reason and normalized_finish_reason not in {
        "STOP",
        "FINISH_REASON_UNSPECIFIED",
    }:
        raise RuntimeError(
            "The citation coverage model stopped before completing "
            f"its assessment (finish_reason={finish_reason})."
        )

    raw_output = (response.text or "").strip()

    if not raw_output:
        raise RuntimeError(
            "The citation coverage model returned an empty response."
        )

    parsed_value = response.parsed

    if isinstance(parsed_value, CitationCoverageOutput):
        parsed = parsed_value
    elif parsed_value is not None:
        parsed = CitationCoverageOutput.model_validate(parsed_value)
    else:
        parsed = CitationCoverageOutput.model_validate_json(raw_output)

    usage = response.usage_metadata

    return ProviderExecution(
        parsed=parsed,
        raw_output=raw_output,
        input_tokens=getattr(usage, "prompt_token_count", None),
        output_tokens=getattr(usage, "candidates_token_count", None),
        total_tokens=getattr(usage, "total_token_count", None),
        thinking_tokens=getattr(usage, "thoughts_token_count", None),
        finish_reason=finish_reason,
    )

def estimate_cost(
    input_tokens: int | None,
    output_tokens: int | None,
    settings: Settings,
    *,
    thinking_tokens: int | None = None,
) -> float | None:
    if input_tokens is None and output_tokens is None:
        return None
    if not (
        settings.evaluator_input_cost_per_million
        or settings.evaluator_output_cost_per_million
    ):
        return None
    input_cost = (input_tokens or 0) * settings.evaluator_input_cost_per_million / 1_000_000
    billable_output_tokens = (output_tokens or 0) + (thinking_tokens or 0)
    output_cost = billable_output_tokens * settings.evaluator_output_cost_per_million / 1_000_000
    return round(input_cost + output_cost, 8)

def estimated_application_cost(
    settings: Settings, evaluator_key: str
) -> float | None:
    """Return a conservative per-application estimate when pricing is configured."""
    if not (
        settings.evaluator_input_cost_per_million
        or settings.evaluator_output_cost_per_million
    ):
        return None
    multiplier = {
        "llm_judge": 1,
        "ragas_faithfulness": 2,
        "ragas_response_relevancy": 4,
        "ragas_context_precision": 4,
        "ragas_context_recall": 2,
        "citation_support": 2,
        "citation_coverage": 2,
    }.get(evaluator_key, 1)
    return round(
        multiplier
        * (
            6_000 * settings.evaluator_input_cost_per_million / 1_000_000
            + 1_500 * settings.evaluator_output_cost_per_million / 1_000_000
        ),
        8,
    )

def _dimension_payload(value: RubricDimension) -> dict[str, Any]:
    return {"score": value.score, "reason": value.reason}

def run_llm_judge(
    item: EvaluationInput,
    settings: Settings,
    provider: JudgeProvider = generate_judge_with_gemini,
) -> AdvancedExecution:
    started = time.perf_counter()
    prompt = build_judge_prompt(item)
    execution = provider(prompt, settings)
    parsed = execution.parsed
    dimensions = {
        "correctness": _dimension_payload(parsed.correctness),
        "completeness": _dimension_payload(parsed.completeness),
        "faithfulness": _dimension_payload(parsed.faithfulness),
        "relevance": _dimension_payload(parsed.relevance),
        "answerability": _dimension_payload(parsed.answerability),
    }
    scores = [value["score"] for value in dimensions.values() if value["score"] is not None]
    if not scores:
        raise ValueError("The judge returned no applicable rubric scores.")
    raw_score = sum(scores) / len(scores)
    normalized = raw_score / 4.0
    runtime_ms = round((time.perf_counter() - started) * 1000)
    configuration = {
        "provider": settings.evaluator_provider,
        "model": settings.evaluator_model,
        "temperature": settings.evaluator_temperature,
        "rubric_version": JUDGE_RUBRIC_VERSION,
        "prompt_hash": judge_prompt_hash(),
        "max_output_tokens": 2048,
    }
    details = {
        "dimensions": dimensions,
        "overall_decision": parsed.overall_decision,
        "unsupported_claims": parsed.unsupported_claims,
        "missing_facts": parsed.missing_facts,
        "summary": parsed.summary,
        "raw_scale": "0-4",
        "thinking_tokens": execution.thinking_tokens,
        "finish_reason": execution.finish_reason,
    }
    cost = estimate_cost(
        execution.input_tokens,
        execution.output_tokens,
        settings,
        thinking_tokens=execution.thinking_tokens,
    )
    result = EvaluationResult(
        evaluator_key="llm_judge",
        raw_score=raw_score,
        normalized_score=normalized,
        passed=normalized >= 0.75,
        explanation=parsed.summary,
        details=details,
        runtime_ms=runtime_ms,
        configuration=configuration,
        estimated_cost=cost,
    )
    return AdvancedExecution(
        result=result,
        raw_provider_output=execution.raw_output,
        input_tokens=execution.input_tokens,
        output_tokens=execution.output_tokens,
        total_tokens=execution.total_tokens,
        thinking_tokens=execution.thinking_tokens,
    )

def run_citation_support(
    item: EvaluationInput,
    settings: Settings,
    provider: JudgeProvider = generate_citation_support_with_gemini,
) -> AdvancedExecution:
    """Evaluate factual claims against their specifically cited evidence."""

    started = time.perf_counter()

    statements = extract_cited_statements(
        item.actual_answer,
        item.retrieved_evidence_by_rank,
    )

    if not statements:
        raise ValueError(
            "Citation Support requires at least one citation-bearing statement."
        )

    prompt = build_citation_support_prompt(item)
    execution = provider(prompt, settings)
    parsed = execution.parsed

    if not isinstance(parsed, CitationSupportOutput):
        raise TypeError(
            "Citation Support provider returned an unexpected output schema."
        )

    expected_statement_ids = set(range(1, len(statements) + 1))

    statement_coverage = validate_citation_statement_coverage(
        parsed,
        expected_statement_ids,
    )

    validate_citation_claim_references(parsed, statements)

    valid_citation_ids = {
        citation_id
        for statement in statements
        for citation_id in statement.citation_ids
    }

    scoring = score_citation_support(
        parsed,
        valid_citation_ids,
        evidence_by_rank=item.retrieved_evidence_by_rank,
    )

    normalized = scoring["score"]
    runtime_ms = round((time.perf_counter() - started) * 1000)

    details = {
        "claims": [
            claim.model_dump()
            for claim in parsed.claims
        ],
        "summary": parsed.summary,
        "verdict_counts": scoring["verdict_counts"],
        "total_claims": scoring["total_claims"],
        "assessable_claims": scoring["assessable_claims"],
        "assessment_coverage": scoring["coverage"],
        "statement_coverage": statement_coverage,
        "thinking_tokens": execution.thinking_tokens,
        "finish_reason": execution.finish_reason,
    }

    configuration = {
        "provider": settings.evaluator_provider,
        "model": settings.evaluator_model,
        "temperature": settings.evaluator_temperature,
        "rubric_version": "citation-support-1.0",
        "max_output_tokens": 4096,
    }

    cost = estimate_cost(
        execution.input_tokens,
        execution.output_tokens,
        settings,
        thinking_tokens=execution.thinking_tokens,
    )

    result = EvaluationResult(
        evaluator_key="citation_support",
        raw_score=normalized,
        normalized_score=normalized,

        passed=(
                normalized == 1.0
                and scoring["coverage"] == 1.0
        ) if normalized is not None else None,

        explanation=parsed.summary,
        details=details,
        runtime_ms=runtime_ms,
        configuration=configuration,
        estimated_cost=cost,
        status="completed" if normalized is not None else "skipped",
    )

    return AdvancedExecution(
        result=result,
        raw_provider_output=execution.raw_output,
        input_tokens=execution.input_tokens,
        output_tokens=execution.output_tokens,
        total_tokens=execution.total_tokens,
        thinking_tokens=execution.thinking_tokens,
    )

def run_citation_coverage(
    item: EvaluationInput,
    settings: Settings,
    provider: JudgeProvider = generate_citation_coverage_with_gemini,
) -> AdvancedExecution:
    """Evaluate factual-claim citation coverage in a saved RAG answer."""

    started = time.perf_counter()

    statements = extract_answer_statements(
        item.actual_answer,
        item.retrieved_evidence_by_rank,
    )

    if not statements:
        raise ValueError(
            "Citation Coverage requires a nonempty generated answer."
        )

    prompt = build_citation_coverage_prompt(item)
    execution = provider(prompt, settings)
    parsed = execution.parsed

    if not isinstance(parsed, CitationCoverageOutput):
        raise TypeError(
            "Citation Coverage provider returned an unexpected output schema."
        )

    statement_review = validate_coverage_statement_completeness(
        parsed,
        len(statements),
    )

    normalized_output = normalize_coverage_claim_citations(
        parsed,
        statements,
    )

    scoring = score_citation_coverage(
        normalized_output,
        item.retrieved_evidence_by_rank,
    )

    normalized_score = scoring["score"]
    runtime_ms = round((time.perf_counter() - started) * 1000)

    details = {
        "claims": scoring["claims"],
        "summary": normalized_output.summary,
        "total_claims": scoring["total_claims"],
        "covered_claims": scoring["covered_claims"],
        "uncovered_claims": scoring["uncovered_claims"],
        "statement_review": statement_review,
        "thinking_tokens": execution.thinking_tokens,
        "finish_reason": execution.finish_reason,
    }

    configuration = {
        "provider": settings.evaluator_provider,
        "model": settings.evaluator_model,
        "temperature": settings.evaluator_temperature,
        "rubric_version": "citation-coverage-1.0",
        "max_output_tokens": 4096,
    }

    cost = estimate_cost(
        execution.input_tokens,
        execution.output_tokens,
        settings,
        thinking_tokens=execution.thinking_tokens,
    )

    result = EvaluationResult(
        evaluator_key="citation_coverage",
        raw_score=normalized_score,
        normalized_score=normalized_score,
        passed=(
            normalized_score == 1.0
            if normalized_score is not None
            else None
        ),
        explanation=(
            f"{scoring['covered_claims']} of "
            f"{scoring['total_claims']} factual claims "
            f"have valid saved citations."
            if normalized_score is not None
            else "No factual claims were identified; citation coverage "
                 "is not applicable."
        ),
        details=details,
        runtime_ms=runtime_ms,
        status=(
            "completed"
            if normalized_score is not None
            else "skipped"
        ),
        configuration=configuration,
        estimated_cost=cost,
    )

    return AdvancedExecution(
        result=result,
        raw_provider_output=execution.raw_output,
        input_tokens=execution.input_tokens,
        output_tokens=execution.output_tokens,
        total_tokens=execution.total_tokens,
        thinking_tokens=execution.thinking_tokens,
    )

def build_ragas_scorers(settings: Settings) -> tuple[dict[str, Any], Any | None]:
    os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")
    try:
        from ragas.embeddings import HuggingFaceEmbeddings
        from ragas.llms import llm_factory
        from ragas.metrics.collections import (
            AnswerRelevancy,
            ContextPrecision,
            ContextRecall,
            Faithfulness,
        )
    except (ImportError, ModuleNotFoundError) as error:
        raise RuntimeError(
            "RAGAS 0.4.3 and langchain-community 0.4.1 are required. "
            "Install rag/requirements.txt in the project virtual environment."
        ) from error

    if settings.evaluator_provider != "gemini":
        raise ValueError("The current RAGAS adapter supports EVALUATOR_PROVIDER=gemini.")
    if not settings.llm_api_key:
        raise RuntimeError("Evaluator API key is not configured.")

    client = genai.Client(api_key=settings.llm_api_key)
    try:
        synchronous_llm = llm_factory(
            settings.evaluator_model,
            provider="google",
            client=client,
            temperature=settings.evaluator_temperature,
        )
        llm = AsyncCompatibleRagasLLM(synchronous_llm)
        embeddings = HuggingFaceEmbeddings(model=settings.evaluator_embedding_model)
        scorers = {
            "ragas_faithfulness": Faithfulness(llm=llm),
            "ragas_response_relevancy": AnswerRelevancy(llm=llm, embeddings=embeddings),
            "ragas_context_precision": ContextPrecision(llm=llm),
            "ragas_context_recall": ContextRecall(llm=llm),
        }
    except Exception:
        client.close()
        raise
    return scorers, client

def ragas_arguments(evaluator_key: str, item: EvaluationInput) -> dict[str, Any]:
    if evaluator_key == "ragas_faithfulness":
        return {
            "user_input": item.question,
            "response": item.actual_answer,
            "retrieved_contexts": item.retrieved_contexts,
        }
    if evaluator_key == "ragas_response_relevancy":
        return {"user_input": item.question, "response": item.actual_answer}
    if evaluator_key == "ragas_context_precision":
        return {
            "user_input": item.question,
            "reference": item.expected_answer,
            "retrieved_contexts": item.retrieved_contexts,
        }
    if evaluator_key == "ragas_context_recall":
        return {
            "user_input": item.question,
            "reference": item.expected_answer,
            "retrieved_contexts": item.retrieved_contexts,
        }
    raise KeyError(f"Unsupported RAGAS evaluator {evaluator_key!r}")

def _metric_value(metric_result: Any) -> float:
    value = getattr(metric_result, "value", metric_result)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"RAGAS returned a non-numeric score: {value!r}")
    return float(value)

def run_ragas_metric(
    evaluator_key: str,
    item: EvaluationInput,
    settings: Settings,
    scorer: Any,
) -> AdvancedExecution:
    started = time.perf_counter()
    arguments = ragas_arguments(evaluator_key, item)
    metric_result = scorer.score(**arguments)
    raw_score = _metric_value(metric_result)
    normalized = max(0.0, min(1.0, raw_score))
    reason = getattr(metric_result, "reason", None)
    runtime_ms = round((time.perf_counter() - started) * 1000)
    configuration = {
        "framework": "ragas",
        "framework_version": "0.4.3",
        "provider": settings.evaluator_provider,
        "model": settings.evaluator_model,
        "embedding_model": (
            settings.evaluator_embedding_model
            if evaluator_key == "ragas_response_relevancy"
            else None
        ),
    }
    details = {
        "ragas_metric": evaluator_key,
        "reason": reason,
        "input_fields": list(arguments),
        "usage_note": "RAGAS did not expose provider token usage through this metric result.",
    }
    result = EvaluationResult(
        evaluator_key=evaluator_key,
        raw_score=raw_score,
        normalized_score=normalized,
        passed=None,
        explanation=reason or f"RAGAS returned {normalized:.3f}.",
        details=details,
        runtime_ms=runtime_ms,
        configuration=configuration,
        estimated_cost=None,
    )
    return AdvancedExecution(result=result)

def applicability_reason(evaluator_key: str, item: EvaluationInput) -> str | None:
    if not item.actual_answer.strip():
        return "No generated answer was saved."
    if evaluator_key == "llm_judge":
        return None
    if evaluator_key == "citation_coverage":
        return None
    if evaluator_key == "citation_support":
        statements = extract_cited_statements(
            item.actual_answer,
            item.retrieved_evidence_by_rank,
        )

        if not statements:
            return "Citation Support requires at least one citation-bearing statement."

        return None
    if evaluator_key == "ragas_response_relevancy":
        if not item.is_answerable:
            return "Response Relevancy is skipped for deliberately unanswerable refusal cases."
        return None
    if not item.retrieved_contexts:
        return "This evaluator requires at least one saved retrieved context."
    if evaluator_key == "ragas_faithfulness":
        if not item.is_answerable and normalize_text(item.actual_answer) == normalize_text(REFUSAL_MESSAGE):
            return "Faithfulness is not informative for a claim-free expected refusal."
        return None
    if evaluator_key in {"ragas_context_precision", "ragas_context_recall"}:
        if not item.is_answerable:
            return "This retrieval metric does not apply to a deliberately unanswerable question."
        if item.review_status != "reviewed" or not item.expected_answer.strip():
            return "This evaluator requires a reviewed reference answer."
    return None

def skipped_execution(evaluator_key: str, reason: str) -> AdvancedExecution:
    configuration = definition_for(evaluator_key)["configuration"]
    return AdvancedExecution(
        result=EvaluationResult(
            evaluator_key=evaluator_key,
            raw_score=None,
            normalized_score=None,
            passed=None,
            explanation=reason,
            details={"skip_reason": reason, "applicability": "not_applicable"},
            runtime_ms=0,
            status="skipped",
            configuration=configuration,
            estimated_cost=0.0,
        )
    )

class AdvancedEvaluatorEngine:
    def __init__(
        self,
        settings: Settings,
        *,
        judge_provider: JudgeProvider = generate_judge_with_gemini,
        citation_support_provider: JudgeProvider = generate_citation_support_with_gemini,
        citation_coverage_provider: JudgeProvider = generate_citation_coverage_with_gemini,
        ragas_factory: RagasFactory = build_ragas_scorers,
    ) -> None:
        self.settings = settings
        self.judge_provider = judge_provider
        self.citation_support_provider = citation_support_provider
        self.citation_coverage_provider = citation_coverage_provider
        self.ragas_factory = ragas_factory
        self._ragas_scorers: dict[str, Any] | None = None
        self._ragas_client: Any | None = None

    def close(self) -> None:
        if self._ragas_client is not None:
            self._ragas_client.close()
            self._ragas_client = None
        self._ragas_scorers = None

    def __enter__(self) -> "AdvancedEvaluatorEngine":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _scorer(self, evaluator_key: str) -> Any:
        if self._ragas_scorers is None:
            self._ragas_scorers, self._ragas_client = self.ragas_factory(self.settings)
        return self._ragas_scorers[evaluator_key]

    def run(self, evaluator_key: str, item: EvaluationInput) -> AdvancedExecution:
        if evaluator_key not in ADVANCED_EVALUATOR_KEYS:
            raise ValueError(f"Unknown advanced evaluator {evaluator_key!r}")
        reason = applicability_reason(evaluator_key, item)
        if reason:
            return skipped_execution(evaluator_key, reason)
        started = time.perf_counter()
        try:
            if evaluator_key == "llm_judge":
                return run_llm_judge(
                    item,
                    self.settings,
                    self.judge_provider,
                )

            if evaluator_key == "citation_support":
                return run_citation_support(
                    item,
                    self.settings,
                    self.citation_support_provider,
                )

            if evaluator_key == "citation_coverage":
                return run_citation_coverage(
                    item,
                    self.settings,
                    self.citation_coverage_provider,
                )

            return run_ragas_metric(
                evaluator_key,
                item,
                self.settings,
                self._scorer(evaluator_key),
            )
        except Exception as error:
            runtime_ms = round((time.perf_counter() - started) * 1000)
            configuration = definition_for(evaluator_key)["configuration"]
            return AdvancedExecution(
                result=EvaluationResult(
                    evaluator_key=evaluator_key,
                    raw_score=None,
                    normalized_score=None,
                    passed=None,
                    explanation="Advanced evaluator failed; inspect the stored error.",
                    details={"failure_scope": "evaluator_only"},
                    runtime_ms=runtime_ms,
                    status="failed",
                    error_message=str(error),
                    configuration=configuration,
                    estimated_cost=None,
                )
            )
