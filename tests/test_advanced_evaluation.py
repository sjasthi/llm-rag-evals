"""Provider-free tests for FP8 advanced evaluation contracts and adapters."""

from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "rag"))

from advanced_evaluation import (  # noqa: E402
    AdvancedEvaluatorEngine,
    JudgeRubricOutput,
    ProviderExecution,
    RubricDimension,
    applicability_reason,
    build_judge_prompt,
    estimate_cost,
    ragas_arguments,
    run_llm_judge,
)
from evaluation import EvaluationInput  # noqa: E402
from evaluator_catalog import ALL_DEFINITIONS, definition_for  # noqa: E402
from llm import REFUSAL_MESSAGE  # noqa: E402
from settings import load_settings  # noqa: E402


def sample_input(**overrides: object) -> EvaluationInput:
    values = {
        "response_id": 17,
        "question": "When does Summer 2026 open registration begin?",
        "expected_answer": "Open registration begins Monday, April 6, 2026.",
        "actual_answer": "It begins on Monday, April 6, 2026.",
        "expected_source": "summer_2026.txt",
        "retrieved_sources": ["summer_2026.txt"],
        "accepted_answers": ["April 6, 2026"],
        "required_facts": ["April 6, 2026"],
        "is_answerable": True,
        "expected_evidence": "Monday, April 6, 2026 - open registration begins",
        "retrieved_contexts": ["Open registration begins Monday, April 6, 2026."],
        "review_status": "reviewed",
    }
    values.update(overrides)
    return EvaluationInput(**values)  # type: ignore[arg-type]


def judge_output() -> JudgeRubricOutput:
    return JudgeRubricOutput(
        correctness=RubricDimension(score=4, reason="The date matches."),
        completeness=RubricDimension(score=4, reason="The required date is included."),
        faithfulness=RubricDimension(score=4, reason="The context supports the date."),
        relevance=RubricDimension(score=4, reason="It directly answers the question."),
        answerability=RubricDimension(score=4, reason="The answerable case was answered."),
        overall_decision="acceptable",
        unsupported_claims=[],
        missing_facts=[],
        summary="The response is supported and complete.",
    )


class AdvancedEvaluationTests(unittest.TestCase):
    def test_catalog_has_unique_score_contracts_for_thirteen_evaluators(self) -> None:
        keys = [definition["key"] for definition in ALL_DEFINITIONS]
        self.assertEqual(13, len(keys))
        self.assertEqual(len(keys), len(set(keys)))
        for key in keys:
            configuration = definition_for(key)["configuration"]
            self.assertTrue(configuration["comparison_target"])
            self.assertTrue(configuration["calculation"])
            self.assertIn("threshold_status", configuration)
            self.assertTrue(configuration["limitation"])

    def test_judge_prompt_contains_saved_inputs_and_rubric_version(self) -> None:
        prompt = build_judge_prompt(sample_input())
        self.assertIn("April 6, 2026", prompt)
        self.assertIn("Retrieved context 1", prompt)
        self.assertIn("Rubric version: 1.0", prompt)
        self.assertIn("Do not answer the original question", prompt)

    def test_judge_normalizes_zero_to_four_dimensions(self) -> None:
        settings = replace(
            load_settings(),
            evaluator_input_cost_per_million=1.0,
            evaluator_output_cost_per_million=2.0,
        )

        def provider(_prompt: str, _settings: object) -> ProviderExecution:
            return ProviderExecution(judge_output(), '{"summary":"ok"}', 100, 20, 120)

        execution = run_llm_judge(sample_input(), settings, provider)
        self.assertEqual(1.0, execution.result.normalized_score)
        self.assertTrue(execution.result.passed)
        self.assertEqual("acceptable", execution.result.details["overall_decision"])
        self.assertEqual(0.00014, execution.result.estimated_cost)
        self.assertEqual(120, execution.total_tokens)

    def test_cost_is_unknown_without_usage_and_uses_configured_rates(self) -> None:
        settings = replace(
            load_settings(),
            evaluator_input_cost_per_million=1.0,
            evaluator_output_cost_per_million=2.0,
        )
        self.assertIsNone(estimate_cost(None, None, settings))
        self.assertEqual(0.0005, estimate_cost(100, 200, settings))

    def test_ragas_mapping_uses_saved_context_order(self) -> None:
        item = sample_input(retrieved_contexts=["rank one", "rank two"])
        arguments = ragas_arguments("ragas_context_precision", item)
        self.assertEqual(["rank one", "rank two"], arguments["retrieved_contexts"])
        self.assertEqual(item.expected_answer, arguments["reference"])

    def test_unanswerable_refusal_skips_inapplicable_ragas_metrics(self) -> None:
        item = sample_input(
            expected_answer=REFUSAL_MESSAGE,
            actual_answer=REFUSAL_MESSAGE,
            is_answerable=False,
            required_facts=[],
        )
        self.assertIsNotNone(applicability_reason("ragas_faithfulness", item))
        self.assertIsNotNone(applicability_reason("ragas_response_relevancy", item))
        self.assertIsNotNone(applicability_reason("ragas_context_recall", item))
        self.assertIsNone(applicability_reason("llm_judge", item))

    def test_engine_isolates_one_scorer_failure(self) -> None:
        class FailingScorer:
            def score(self, **_kwargs: object) -> object:
                raise RuntimeError("controlled RAGAS failure")

        def factory(_settings: object) -> tuple[dict[str, object], None]:
            return {
                "ragas_faithfulness": FailingScorer(),
                "ragas_response_relevancy": FailingScorer(),
                "ragas_context_precision": FailingScorer(),
                "ragas_context_recall": FailingScorer(),
            }, None

        with AdvancedEvaluatorEngine(load_settings(), ragas_factory=factory) as engine:
            execution = engine.run("ragas_faithfulness", sample_input())
        self.assertEqual("failed", execution.result.status)
        self.assertIn("controlled RAGAS failure", execution.result.error_message or "")


if __name__ == "__main__":
    unittest.main()
