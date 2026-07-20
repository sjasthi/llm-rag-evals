"""FP8 LLM-judge and RAGAS evaluators for already-saved RAG responses."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from evaluation import EvaluationInput, EvaluationResult, normalize_text
from evaluator_catalog import ADVANCED_DEFINITIONS, definition_for
from llm import REFUSAL_MESSAGE
from settings import Settings


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


@dataclass(frozen=True)
class ProviderExecution:
    parsed: JudgeRubricOutput
    raw_output: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None


@dataclass(frozen=True)
class AdvancedExecution:
    result: EvaluationResult
    raw_provider_output: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


JudgeProvider = Callable[[str, Settings], ProviderExecution]
RagasFactory = Callable[[Settings], tuple[dict[str, Any], Any | None]]


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
    )


def estimate_cost(
    input_tokens: int | None,
    output_tokens: int | None,
    settings: Settings,
) -> float | None:
    if input_tokens is None and output_tokens is None:
        return None
    input_cost = (input_tokens or 0) * settings.evaluator_input_cost_per_million / 1_000_000
    output_cost = (output_tokens or 0) * settings.evaluator_output_cost_per_million / 1_000_000
    return round(input_cost + output_cost, 8)


def estimated_application_cost(settings: Settings, evaluator_key: str) -> float:
    """Conservative preflight estimate; zero means pricing was not configured."""
    multiplier = {
        "llm_judge": 1,
        "ragas_faithfulness": 2,
        "ragas_response_relevancy": 4,
        "ragas_context_precision": 4,
        "ragas_context_recall": 2,
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
    }
    details = {
        "dimensions": dimensions,
        "overall_decision": parsed.overall_decision,
        "unsupported_claims": parsed.unsupported_claims,
        "missing_facts": parsed.missing_facts,
        "summary": parsed.summary,
        "raw_scale": "0-4",
    }
    cost = estimate_cost(execution.input_tokens, execution.output_tokens, settings)
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
        llm = llm_factory(
            settings.evaluator_model,
            provider="google",
            client=client,
            temperature=settings.evaluator_temperature,
        )
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
        ragas_factory: RagasFactory = build_ragas_scorers,
    ) -> None:
        self.settings = settings
        self.judge_provider = judge_provider
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
                return run_llm_judge(item, self.settings, self.judge_provider)
            return run_ragas_metric(
                evaluator_key, item, self.settings, self._scorer(evaluator_key)
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
