"""Provider-free tests for FP8 advanced evaluation contracts and adapters."""

from __future__ import annotations

import asyncio
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from ragas.llms.base import InstructorBaseRagasLLM


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "rag"))

from advanced_evaluation import (  # noqa: E402
    AsyncCompatibleRagasLLM,
    AdvancedEvaluatorEngine,
    JudgeRubricOutput,
    ProviderExecution,
    RubricDimension,
    applicability_reason,
    build_judge_prompt,
    estimate_cost,
    estimated_application_cost,
    ragas_arguments,
    run_llm_judge,
)
from evaluation import EvaluationInput  # noqa: E402
from evaluator_catalog import ALL_DEFINITIONS, definition_for  # noqa: E402
from evaluate_saved_run import LOCAL_EVALUATOR_KEYS, build_local_preflight  # noqa: E402
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
    def test_saved_run_local_preflight_separates_reuse_and_run(self) -> None:
        with patch(
            "evaluate_saved_run.reusable_result_exists",
            side_effect=lambda _connection, _response_id, key: key == LOCAL_EVALUATOR_KEYS[0],
        ):
            preflight = build_local_preflight(object(), [19], force=False)

        self.assertEqual(len(LOCAL_EVALUATOR_KEYS), len(preflight["applications"]))
        self.assertEqual(1, preflight["reused_count"])
        self.assertEqual(
            len(LOCAL_EVALUATOR_KEYS) - preflight["reused_count"],
            preflight["application_count"],
        )
        self.assertEqual(0, preflight["paid_application_count"])
        store = (PROJECT_ROOT / "rag" / "evaluation_store.py").read_text(encoding="utf-8")
        self.assertIn("result.status IN ('completed', 'skipped')", store)

    def test_ragas_llm_adapter_supplies_async_generation_for_sync_client(self) -> None:
        calls: list[tuple[str, object]] = []

        class SynchronousLLM:
            def generate(self, prompt: str, response_model: object) -> dict[str, str]:
                calls.append((prompt, response_model))
                return {"result": "structured"}

        response_model = object()
        adapter = AsyncCompatibleRagasLLM(SynchronousLLM())
        self.assertIsInstance(adapter, InstructorBaseRagasLLM)
        result = asyncio.run(adapter.agenerate("evaluate this", response_model))

        self.assertEqual({"result": "structured"}, result)
        self.assertEqual([("evaluate this", response_model)], calls)

    def test_catalog_has_unique_score_contracts_for_all_evaluators(self) -> None:
        keys = [definition["key"] for definition in ALL_DEFINITIONS]

        self.assertEqual(17, len(keys))
        self.assertIn("citation_validity", keys)
        self.assertIn("citation_presence", keys)
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

    def test_judge_cost_includes_thinking_tokens(self) -> None:
        settings = replace(
            load_settings(),
            evaluator_input_cost_per_million=1.0,
            evaluator_output_cost_per_million=2.0,
        )

        def provider(_prompt: str, _settings: object) -> ProviderExecution:
            return ProviderExecution(
                judge_output(), '{"summary":"ok"}', 100, 20, 150, 30, "STOP"
            )

        execution = run_llm_judge(sample_input(), settings, provider)

        self.assertEqual(0.0002, execution.result.estimated_cost)
        self.assertEqual(30, execution.result.details["thinking_tokens"])
        self.assertEqual(150, execution.total_tokens)

    def test_cost_is_unknown_without_usage_and_uses_configured_rates(self) -> None:
        settings = replace(
            load_settings(),
            evaluator_input_cost_per_million=1.0,
            evaluator_output_cost_per_million=2.0,
        )
        self.assertIsNone(estimate_cost(None, None, settings))
        self.assertEqual(0.0005, estimate_cost(100, 200, settings))

        unpriced = replace(
            settings,
            evaluator_input_cost_per_million=0.0,
            evaluator_output_cost_per_million=0.0,
        )
        self.assertIsNone(estimate_cost(100, 200, unpriced))
        self.assertIsNone(estimated_application_cost(unpriced, "llm_judge"))

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

    def test_citation_support_output_schema(self):
        from advanced_evaluation import (
            CitationSupportClaim,
            CitationSupportOutput,
        )

        output = CitationSupportOutput(
            claims=[
                CitationSupportClaim(
                    statement_id=1,
                    claim="Registration Review takes 2 business days.",
                    citation_ids=[1],
                    verdict="supported",
                    explanation="The cited evidence states 2 business days.",
                ),
            ],
            summary="The claim is supported.",
        )

        self.assertEqual(len(output.claims), 1)
        self.assertEqual(output.claims[0].citation_ids, [1])
        self.assertEqual(output.claims[0].verdict, "supported")

    def test_citation_support_prompt_uses_only_cited_evidence(self):
        from advanced_evaluation import build_citation_support_prompt
        from evaluation import EvaluationInput

        item = EvaluationInput(
            response_id=158,
            question="How long does Registration Review take?",
            expected_answer="",
            actual_answer=(
                "Registration Review takes 2 business days "
                "and is handled by Advising [1]."
            ),
            expected_source=None,
            retrieved_sources=[],
            accepted_answers=[],
            required_facts=[],
            is_answerable=True,
            retrieved_evidence_by_rank={
                1: "Registration Review | 2 business days | Advising",
                2: "Unrelated information about tuition payment deadlines.",
            },
        )

        prompt = build_citation_support_prompt(item)

        self.assertIn("Registration Review | 2 business days | Advising", prompt)
        self.assertIn('"citation_ids": [', prompt)
        self.assertNotIn(
            "Unrelated information about tuition payment deadlines.",
            prompt,
        )
        self.assertIn("Separate compound statements", prompt)

    def test_citation_support_provider_uses_structured_json(self):
        from unittest.mock import MagicMock, patch
        from advanced_evaluation import (
            CitationSupportOutput,
            generate_citation_support_with_gemini,
        )

        settings = MagicMock()
        settings.evaluator_provider = "gemini"
        settings.llm_api_key = "test-key"
        settings.evaluator_model = "test-model"
        settings.evaluator_temperature = 0.0

        response = MagicMock()
        response.text = (
            '{"claims":[{"statement_id":1,'
            '"claim":"Registration takes two days.",'
            '"citation_ids":[1],"verdict":"supported",'
            '"explanation":"Source confirms two days."}],'
            '"summary":"The claim is supported."}'
        )
        response.parsed = None
        response.candidates = []
        response.usage_metadata.prompt_token_count = 100
        response.usage_metadata.candidates_token_count = 50
        response.usage_metadata.total_token_count = 150
        response.usage_metadata.thoughts_token_count = 0

        with patch("advanced_evaluation.genai.Client") as client_class:
            client = client_class.return_value
            client.models.generate_content.return_value = response

            execution = generate_citation_support_with_gemini(
                "Evaluate the cited claim.",
                settings,
            )

            self.assertIsInstance(execution.parsed, CitationSupportOutput)
            self.assertEqual(execution.parsed.claims[0].verdict, "supported")
            self.assertEqual(execution.input_tokens, 100)
            self.assertEqual(execution.output_tokens, 50)
            client.close.assert_called_once()

    def test_citation_support_scoring_all_supported(self):
        from advanced_evaluation import (
            CitationSupportClaim,
            CitationSupportOutput,
            score_citation_support,
        )

        output = CitationSupportOutput(
            claims=[
                CitationSupportClaim(
                    statement_id=1,
                    claim="Registration takes two days.",
                    citation_ids=[1],
                    verdict="supported",
                    explanation="Source confirms the duration.",
                ),
                CitationSupportClaim(
                    statement_id=2,
                    claim="Advising handles registration review.",
                    citation_ids=[1],
                    verdict="supported",
                    explanation="Source identifies Advising.",
                ),
            ],
            summary="All claims supported.",
        )

        result = score_citation_support(output, {1, 2, 3})

        self.assertEqual(result["score"], 1.0)
        self.assertEqual(result["coverage"], 1.0)
        self.assertEqual(result["total_claims"], 2)

    def test_citation_support_scoring_partial_support(self):
        from advanced_evaluation import (
            CitationSupportClaim,
            CitationSupportOutput,
            score_citation_support,
        )

        output = CitationSupportOutput(
            claims=[
                CitationSupportClaim(
                    statement_id=1,
                    claim="Registration takes two days.",
                    citation_ids=[1],
                    verdict="supported",
                    explanation="Supported.",
                ),
                CitationSupportClaim(
                    statement_id=2,
                    claim="Registration takes three days.",
                    citation_ids=[1],
                    verdict="contradicted",
                    explanation="Source says two days.",
                ),
                CitationSupportClaim(
                    statement_id=3,
                    claim="Registration is free.",
                    citation_ids=[1],
                    verdict="insufficient_evidence",
                    explanation="Source does not mention fees.",
                ),
                CitationSupportClaim(
                    statement_id=4,
                    claim="An unreadable chart contains a deadline.",
                    citation_ids=[2],
                    verdict="unassessable",
                    explanation="Chart content is unavailable.",
                ),
            ],
            summary="Mixed support.",
        )

        result = score_citation_support(output, {1, 2})

        self.assertAlmostEqual(result["score"], 1 / 3)
        self.assertEqual(result["coverage"], 0.75)
        self.assertEqual(result["assessable_claims"], 3)

    def test_citation_support_rejects_unknown_citation_ids(self):
        from advanced_evaluation import (
            CitationSupportClaim,
            CitationSupportOutput,
            score_citation_support,
        )

        output = CitationSupportOutput(
            claims=[
                CitationSupportClaim(
                    statement_id=1,
                    claim="Registration takes two days.",
                    citation_ids=[99],
                    verdict="supported",
                    explanation="Claimed support.",
                ),
            ],
            summary="Test.",
        )

        with self.assertRaises(ValueError):
            score_citation_support(output, {1, 2, 3})

    def test_citation_support_rejects_empty_claims(self):
        from advanced_evaluation import (
            CitationSupportOutput,
            score_citation_support,
        )

        output = CitationSupportOutput(
            claims=[],
            summary="No claims.",
        )

        with self.assertRaises(ValueError):
            score_citation_support(output, {1})

    def test_citation_support_rejects_supported_claim_without_evidence(self):
        from advanced_evaluation import (
            CitationSupportClaim,
            CitationSupportOutput,
            score_citation_support,
        )

        output = CitationSupportOutput(
            claims=[
                CitationSupportClaim(
                    statement_id=1,
                    claim="Registration takes two days.",
                    citation_ids=[4],
                    verdict="supported",
                    explanation="Claimed support.",
                ),
            ],
            summary="Test.",
        )

        with self.assertRaises(ValueError):
            score_citation_support(
                output,
                valid_citation_ids={1, 2, 3, 4},
                evidence_by_rank={
                    1: "Registration takes two days.",
                    2: "Other information.",
                    3: "Additional information.",
                },
            )

    def test_citation_support_statement_coverage_complete(self):
        from advanced_evaluation import (
            CitationSupportClaim,
            CitationSupportOutput,
            validate_citation_statement_coverage,
        )

        output = CitationSupportOutput(
            claims=[
                CitationSupportClaim(
                    statement_id=1,
                    claim="Registration takes two days.",
                    citation_ids=[1],
                    verdict="supported",
                    explanation="Supported by Source 1.",
                ),
                CitationSupportClaim(
                    statement_id=2,
                    claim="Advising is required.",
                    citation_ids=[2],
                    verdict="supported",
                    explanation="Supported by Source 2.",
                ),
            ],
            summary="All statements evaluated.",
        )

        result = validate_citation_statement_coverage(
            output,
            expected_statement_ids={1, 2},
        )

        self.assertEqual(result["statement_coverage"], 1.0)
        self.assertEqual(result["covered_statements"], 2)

    def test_citation_support_statement_coverage_rejects_omission(self):
        from advanced_evaluation import (
            CitationSupportClaim,
            CitationSupportOutput,
            validate_citation_statement_coverage,
        )

        output = CitationSupportOutput(
            claims=[
                CitationSupportClaim(
                    statement_id=1,
                    claim="Registration takes two days.",
                    citation_ids=[1],
                    verdict="supported",
                    explanation="Supported by Source 1.",
                ),
            ],
            summary="Incomplete evaluation.",
        )

        with self.assertRaises(ValueError):
            validate_citation_statement_coverage(
                output,
                expected_statement_ids={1, 2},
            )

    def test_citation_support_accepts_matching_statement_citations(self):
        from advanced_evaluation import (
            CitationSupportClaim,
            CitationSupportOutput,
            validate_citation_claim_references,
        )
        from citation_support import extract_cited_statements

        statements = extract_cited_statements(
            "Registration takes two days [1]. Advising is required [2].",
            {
                1: "Registration takes two days.",
                2: "Advising is required.",
            },
        )

        output = CitationSupportOutput(
            claims=[
                CitationSupportClaim(
                    statement_id=1,
                    claim="Registration takes two days.",
                    citation_ids=[1],
                    verdict="supported",
                    explanation="Source 1 confirms the duration.",
                ),
                CitationSupportClaim(
                    statement_id=2,
                    claim="Advising is required.",
                    citation_ids=[2],
                    verdict="supported",
                    explanation="Source 2 confirms the requirement.",
                ),
            ],
            summary="Both claims supported.",
        )

        validate_citation_claim_references(output, statements)

    def test_citation_support_rejects_cross_statement_citations(self):
        from advanced_evaluation import (
            CitationSupportClaim,
            CitationSupportOutput,
            validate_citation_claim_references,
        )
        from citation_support import extract_cited_statements

        statements = extract_cited_statements(
            "Registration takes two days [1]. Advising is required [2].",
            {
                1: "Registration takes two days.",
                2: "Advising is required.",
            },
        )

        output = CitationSupportOutput(
            claims=[
                CitationSupportClaim(
                    statement_id=1,
                    claim="Registration takes two days.",
                    citation_ids=[2],
                    verdict="supported",
                    explanation="Incorrectly references Source 2.",
                ),
                CitationSupportClaim(
                    statement_id=2,
                    claim="Advising is required.",
                    citation_ids=[2],
                    verdict="supported",
                    explanation="Source 2 confirms the requirement.",
                ),
            ],
            summary="Test incorrect citation matching.",
        )

        with self.assertRaises(ValueError):
            validate_citation_claim_references(output, statements)

    def test_run_citation_support_with_mocked_provider(self):
        from unittest.mock import MagicMock
        from advanced_evaluation import (
            CitationSupportClaim,
            CitationSupportOutput,
            ProviderExecution,
            run_citation_support,
        )
        from evaluation import EvaluationInput

        item = EvaluationInput(
            response_id=158,
            question="How long does Registration Review take?",
            expected_answer="",
            actual_answer=(
                "Registration Review takes 2 business days "
                "and Advising is responsible [1]."
            ),
            expected_source=None,
            retrieved_sources=[],
            accepted_answers=[],
            required_facts=[],
            is_answerable=True,
            retrieved_evidence_by_rank={
                1: "Registration Review | 2 business days | Advising",
            },
        )

        settings = MagicMock()
        settings.evaluator_provider = "gemini"
        settings.evaluator_model = "test-model"
        settings.evaluator_temperature = 0.0
        settings.evaluator_input_cost_per_million = 1.0
        settings.evaluator_output_cost_per_million = 2.0

        parsed = CitationSupportOutput(
            claims=[
                CitationSupportClaim(
                    statement_id=1,
                    claim="Registration Review takes 2 business days.",
                    citation_ids=[1],
                    verdict="supported",
                    explanation="Source confirms 2 business days.",
                ),
                CitationSupportClaim(
                    statement_id=1,
                    claim="Advising is responsible.",
                    citation_ids=[1],
                    verdict="supported",
                    explanation="Source identifies Advising.",
                ),
            ],
            summary="Both claims are supported.",
        )

        def fake_provider(prompt, provider_settings):
            self.assertIn("Registration Review", prompt)

            return ProviderExecution(
                parsed=parsed,
                raw_output=parsed.model_dump_json(),
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                thinking_tokens=0,
                finish_reason="STOP",
            )

        execution = run_citation_support(
            item,
            settings,
            provider=fake_provider,
        )

        self.assertEqual(execution.result.evaluator_key, "citation_support")
        self.assertEqual(execution.result.normalized_score, 1.0)
        self.assertTrue(execution.result.passed)
        self.assertEqual(execution.result.details["total_claims"], 2)
        self.assertEqual(execution.result.details["assessment_coverage"], 1.0)
        self.assertEqual(execution.input_tokens, 100)
        self.assertEqual(execution.output_tokens, 50)
        self.assertEqual(execution.result.status, "completed")

    def test_engine_runs_citation_support_with_mocked_provider(self):
        from unittest.mock import MagicMock

        from advanced_evaluation import (
            AdvancedEvaluatorEngine,
            CitationSupportClaim,
            CitationSupportOutput,
            ProviderExecution,
        )
        from evaluation import EvaluationInput

        item = EvaluationInput(
            response_id=158,
            question="How long does Registration Review take?",
            expected_answer="",
            actual_answer="Registration Review takes 2 business days [1].",
            expected_source=None,
            retrieved_sources=[],
            accepted_answers=[],
            required_facts=[],
            is_answerable=True,
            retrieved_evidence_by_rank={
                1: "Registration Review takes 2 business days.",
            },
        )

        settings = MagicMock()
        settings.evaluator_provider = "gemini"
        settings.evaluator_model = "test-model"
        settings.evaluator_temperature = 0.0
        settings.evaluator_input_cost_per_million = 1.0
        settings.evaluator_output_cost_per_million = 2.0

        parsed = CitationSupportOutput(
            claims=[
                CitationSupportClaim(
                    statement_id=1,
                    claim="Registration Review takes 2 business days.",
                    citation_ids=[1],
                    verdict="supported",
                    explanation="The cited evidence confirms the duration.",
                ),
            ],
            summary="The claim is supported.",
        )

        provider_calls = []

        def fake_provider(prompt, provider_settings):
            provider_calls.append(prompt)

            return ProviderExecution(
                parsed=parsed,
                raw_output=parsed.model_dump_json(),
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                thinking_tokens=0,
                finish_reason="STOP",
            )

        with AdvancedEvaluatorEngine(
                settings,
                citation_support_provider=fake_provider,
        ) as engine:
            execution = engine.run("citation_support", item)

        self.assertEqual(len(provider_calls), 1)
        self.assertEqual(execution.result.evaluator_key, "citation_support")
        self.assertEqual(execution.result.status, "completed")
        self.assertEqual(execution.result.normalized_score, 1.0)
        self.assertTrue(execution.result.passed)
        self.assertEqual(execution.result.details["total_claims"], 1)
        self.assertEqual(execution.input_tokens, 100)
        self.assertEqual(execution.output_tokens, 50)

    def test_citation_support_is_opt_in(self):
        from advanced_evaluation import ADVANCED_EVALUATOR_KEYS
        from run_advanced_evaluation import DEFAULT_ADVANCED_EVALUATOR_KEYS

        self.assertIn("citation_support", ADVANCED_EVALUATOR_KEYS)
        self.assertNotIn("citation_support", DEFAULT_ADVANCED_EVALUATOR_KEYS)
        self.assertEqual(5, len(DEFAULT_ADVANCED_EVALUATOR_KEYS))

    def test_citation_support_rejects_paid_execution_without_authorization(self):
        from unittest.mock import MagicMock
        from run_advanced_evaluation import execute_plan

        settings = MagicMock()
        preflight = {
            "paid_application_count": 1,
            "estimated_cost": None,
            "applications": [
                {
                    "response_id": 158,
                    "evaluator": "citation_support",
                    "action": "run",
                    "attempts": 1,
                }
            ],
        }

        with self.assertRaisesRegex(ValueError, "requires --allow-paid"):
            execute_plan(
                settings,
                preflight,
                allow_paid=False,
            )

    def test_citation_support_rejects_unknown_cost_without_authorization(self):
        from unittest.mock import MagicMock
        from run_advanced_evaluation import execute_plan

        settings = MagicMock()
        preflight = {
            "paid_application_count": 1,
            "estimated_cost": None,
            "applications": [
                {
                    "response_id": 158,
                    "evaluator": "citation_support",
                    "action": "run",
                    "attempts": 1,
                }
            ],
        }

        with self.assertRaisesRegex(ValueError, "cost is unknown"):
            execute_plan(
                settings,
                preflight,
                allow_paid=True,
                allow_unknown_cost=False,
            )

    def test_citation_support_preflight_loads_without_gold_standard(self):
        from unittest.mock import MagicMock, patch

        from run_advanced_evaluation import build_preflight

        settings = MagicMock()
        connection = MagicMock()

        item = MagicMock()
        item.actual_answer = "Registration Review takes 2 business days [1]."
        item.retrieved_evidence_by_rank = {
            1: "Registration Review takes 2 business days."
        }

        with (
            patch(
                "run_advanced_evaluation.load_evaluation_input",
                return_value=item,
            ) as mock_load,
            patch(
                "run_advanced_evaluation.reusable_result_exists",
                return_value=False,
            ),
            patch(
                "run_advanced_evaluation.estimated_application_cost",
                return_value=0.0075,
            ),
        ):
            preflight = build_preflight(
                settings,
                connection,
                response_ids=[158],
                evaluator_keys=["citation_support"],
                attempts=1,
                force=False,
            )

        mock_load.assert_called_once_with(
            connection,
            158,
            require_expected_answer=False,
        )

        self.assertEqual(preflight["paid_application_count"], 1)
        self.assertEqual(preflight["applications"][0]["action"], "run")
        self.assertEqual(preflight["estimated_cost"], 0.0075)

    def test_citation_support_cli_executes_and_persists_with_mocks(self):
        from dataclasses import asdict
        from unittest.mock import MagicMock, patch

        from advanced_evaluation import AdvancedExecution
        from evaluation import EvaluationResult
        from run_advanced_evaluation import execute_plan

        settings = MagicMock()

        preflight = {
            "paid_application_count": 1,
            "estimated_cost": 0.0075,
            "applications": [
                {
                    "response_id": 158,
                    "evaluator": "citation_support",
                    "action": "run",
                    "attempts": 1,
                }
            ],
        }

        item = MagicMock()
        item.actual_answer = "Registration Review takes 2 business days [1]."
        item.retrieved_evidence_by_rank = {
            1: "Registration Review takes 2 business days."
        }

        result = EvaluationResult(
            evaluator_key="citation_support",
            raw_score=1.0,
            normalized_score=1.0,
            passed=True,
            explanation="The cited claim is supported.",
            details={
                "total_claims": 1,
                "assessable_claims": 1,
                "assessment_coverage": 1.0,
            },
            runtime_ms=12,
            configuration={
                "provider": "gemini",
                "model": "mock-model",
            },
            estimated_cost=0.0001,
            status="completed",
        )

        execution = AdvancedExecution(
            result=result,
            raw_provider_output='{"summary":"The cited claim is supported."}',
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            thinking_tokens=0,
        )

        mock_connection = MagicMock()
        mock_engine = MagicMock()
        mock_engine.run.return_value = execution

        mock_engine_context = MagicMock()
        mock_engine_context.__enter__.return_value = mock_engine

        with (
            patch(
                "run_advanced_evaluation.AdvancedEvaluatorEngine",
                return_value=mock_engine_context,
            ),
            patch(
                "run_advanced_evaluation.database_connection",
            ) as mock_database,
            patch(
                "run_advanced_evaluation.load_evaluation_input",
                return_value=item,
            ) as mock_load,
            patch(
                "run_advanced_evaluation.persist_result",
                return_value=1,
            ) as mock_persist,
            patch(
                "run_advanced_evaluation.active_evaluator",
                return_value={"evaluator_id": 16},
            ),
        ):
            mock_database.return_value.__enter__.return_value = mock_connection

            outcomes = execute_plan(
                settings,
                preflight,
                allow_paid=True,
                allow_unknown_cost=False,
            )

        mock_load.assert_called_once_with(
            mock_connection,
            158,
            require_expected_answer=False,
        )

        mock_engine.run.assert_called_once_with("citation_support", item)

        mock_persist.assert_called_once_with(
            mock_connection,
            response_id=158,
            result=execution.result,
            raw_provider_output=execution.raw_provider_output,
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )

        mock_connection.start_transaction.assert_called_once()
        mock_connection.commit.assert_called_once()
        mock_connection.rollback.assert_not_called()

        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0]["response_id"], 158)
        self.assertEqual(outcomes[0]["evaluator"], "citation_support")
        self.assertEqual(outcomes[0]["attempt_number"], 1)
        self.assertEqual(outcomes[0]["result"]["status"], "completed")
        self.assertEqual(outcomes[0]["usage"]["total_tokens"], 150)

    def test_missing_evaluator_registration_blocks_paid_execution(self):
        from unittest.mock import MagicMock, patch

        from run_advanced_evaluation import execute_plan

        settings = MagicMock()

        preflight = {
            "paid_application_count": 1,
            "estimated_cost": 0.0075,
            "applications": [
                {
                    "response_id": 158,
                    "evaluator": "citation_support",
                    "action": "run",
                    "attempts": 1,
                }
            ],
        }

        mock_connection = MagicMock()

        with (
            patch(
                "run_advanced_evaluation.database_connection"
            ) as mock_database,
            patch(
                "run_advanced_evaluation.active_evaluator",
                side_effect=ValueError(
                    "Evaluator definition 'citation_support' is not seeded."
                ),
            ),
            patch(
                "run_advanced_evaluation.AdvancedEvaluatorEngine"
            ) as mock_engine,
            patch(
                "run_advanced_evaluation.persist_result"
            ) as mock_persist,
        ):
            mock_database.return_value.__enter__.return_value = mock_connection

            with self.assertRaisesRegex(
                    ValueError,
                    "not seeded",
            ):
                execute_plan(
                    settings,
                    preflight,
                    allow_paid=True,
                    allow_unknown_cost=False,
                )

        mock_engine.assert_not_called()
        mock_persist.assert_not_called()

    def test_citation_support_insufficient_evidence_scores_zero(self):
        from advanced_evaluation import (
            CitationSupportClaim,
            CitationSupportOutput,
            score_citation_support,
        )

        output = CitationSupportOutput(
            claims=[
                CitationSupportClaim(
                    statement_id=1,
                    claim="Registration Review takes 5 business days.",
                    citation_ids=[1],
                    verdict="insufficient_evidence",
                    explanation="The cited source does not specify a processing time.",
                )
            ],
            summary="The claim is not supported by the cited evidence.",
        )

        scoring = score_citation_support(
            output,
            valid_citation_ids={1},
            evidence_by_rank={1: "Contact the Advising office for assistance."},
        )

        self.assertEqual(scoring["score"], 0.0)
        self.assertEqual(scoring["coverage"], 1.0)
        self.assertEqual(scoring["verdict_counts"]["insufficient_evidence"], 1)

    def test_citation_support_contradicted_claim_scores_zero(self):
        from advanced_evaluation import (
            CitationSupportClaim,
            CitationSupportOutput,
            score_citation_support,
        )

        output = CitationSupportOutput(
            claims=[
                CitationSupportClaim(
                    statement_id=1,
                    claim="Registration Review takes 5 business days.",
                    citation_ids=[1],
                    verdict="contradicted",
                    explanation="The cited source specifies 2 business days.",
                )
            ],
            summary="The claim contradicts the cited evidence.",
        )

        scoring = score_citation_support(
            output,
            valid_citation_ids={1},
            evidence_by_rank={
                1: "Registration Review takes 2 business days."
            },
        )

        self.assertEqual(scoring["score"], 0.0)
        self.assertEqual(scoring["coverage"], 1.0)
        self.assertEqual(scoring["verdict_counts"]["contradicted"], 1)

    def test_citation_support_mixed_claims_score_half(self):
        from advanced_evaluation import (
            CitationSupportClaim,
            CitationSupportOutput,
            score_citation_support,
        )

        output = CitationSupportOutput(
            claims=[
                CitationSupportClaim(
                    statement_id=1,
                    claim="Registration Review takes 2 business days.",
                    citation_ids=[1],
                    verdict="supported",
                    explanation="The processing time matches the source.",
                ),
                CitationSupportClaim(
                    statement_id=1,
                    claim="The Registrar handles Registration Review.",
                    citation_ids=[1],
                    verdict="contradicted",
                    explanation="The source identifies Advising instead.",
                ),
            ],
            summary="One claim is supported and one is contradicted.",
        )

        scoring = score_citation_support(
            output,
            valid_citation_ids={1},
            evidence_by_rank={
                1: (
                    "Registration Review takes 2 business days. "
                    "Responsible office: Advising."
                )
            },
        )

        self.assertEqual(scoring["score"], 0.5)
        self.assertEqual(scoring["coverage"], 1.0)
        self.assertEqual(scoring["total_claims"], 2)
        self.assertEqual(scoring["assessable_claims"], 2)
        self.assertEqual(scoring["verdict_counts"]["supported"], 1)
        self.assertEqual(scoring["verdict_counts"]["contradicted"], 1)

    def test_extract_answer_statements_includes_uncited_statements(self):
        from citation_support import extract_answer_statements

        answer = (
            "Registration Review takes 2 business days [1]. "
            "Students can complete the process online."
        )

        statements = extract_answer_statements(
            answer,
            {1: "Registration Review takes 2 business days."},
        )

        self.assertEqual(len(statements), 2)
        self.assertTrue(statements[0].has_citation)
        self.assertTrue(statements[0].has_valid_citation)
        self.assertFalse(statements[1].has_citation)
        self.assertFalse(statements[1].has_valid_citation)

    def test_extract_answer_statements_identifies_invalid_citations(self):
        from citation_support import extract_answer_statements

        statements = extract_answer_statements(
            "Registration Review takes 2 business days [99].",
            {1: "Registration Review takes 2 business days."},
        )

        self.assertEqual(len(statements), 1)
        self.assertTrue(statements[0].has_citation)
        self.assertFalse(statements[0].has_valid_citation)
        self.assertEqual(statements[0].missing_citation_ids, [99])

    def test_extract_cited_statements_preserves_existing_behavior(self):
        from citation_support import extract_cited_statements

        statements = extract_cited_statements(
            "Registration Review takes 2 business days [1]. "
            "Students can complete the process online.",
            {1: "Registration Review takes 2 business days."},
        )

        self.assertEqual(len(statements), 1)
        self.assertEqual(statements[0].citation_ids, [1])

    def test_citation_coverage_all_claims_cited(self):
        from citation_coverage import (
            CitationCoverageClaim,
            CitationCoverageOutput,
            score_citation_coverage,
        )

        output = CitationCoverageOutput(
            claims=[
                CitationCoverageClaim(
                    statement_id=1,
                    claim="Registration Review takes 2 business days.",
                    citation_ids=[1],
                ),
                CitationCoverageClaim(
                    statement_id=2,
                    claim="Advising handles Registration Review.",
                    citation_ids=[1],
                ),
            ]
        )

        result = score_citation_coverage(
            output,
            {1: "Registration Review takes 2 business days. Office: Advising."},
        )

        self.assertEqual(result["score"], 1.0)
        self.assertEqual(result["covered_claims"], 2)

    def test_citation_coverage_partially_cited(self):
        from citation_coverage import (
            CitationCoverageClaim,
            CitationCoverageOutput,
            score_citation_coverage,
        )

        output = CitationCoverageOutput(
            claims=[
                CitationCoverageClaim(
                    statement_id=1,
                    claim="Registration Review takes 2 business days.",
                    citation_ids=[1],
                ),
                CitationCoverageClaim(
                    statement_id=2,
                    claim="Students can complete Registration Review online.",
                    citation_ids=[],
                ),
            ]
        )

        result = score_citation_coverage(
            output,
            {1: "Registration Review takes 2 business days."},
        )

        self.assertEqual(result["score"], 0.5)
        self.assertEqual(result["covered_claims"], 1)
        self.assertEqual(result["uncovered_claims"], 1)

    def test_citation_coverage_invalid_citation_is_uncovered(self):
        from citation_coverage import (
            CitationCoverageClaim,
            CitationCoverageOutput,
            score_citation_coverage,
        )

        output = CitationCoverageOutput(
            claims=[
                CitationCoverageClaim(
                    statement_id=1,
                    claim="Registration Review takes 2 business days.",
                    citation_ids=[99],
                )
            ]
        )

        result = score_citation_coverage(
            output,
            {1: "Registration Review takes 2 business days."},
        )

        self.assertEqual(result["score"], 0.0)
        self.assertEqual(result["claims"][0]["invalid_citation_ids"], [99])

    def test_citation_coverage_no_factual_claims_is_not_applicable(self):
        from citation_coverage import (
            CitationCoverageOutput,
            score_citation_coverage,
        )

        result = score_citation_coverage(
            CitationCoverageOutput(claims=[]),
            {1: "Some retrieved evidence."},
        )

        self.assertIsNone(result["score"])
        self.assertEqual(result["total_claims"], 0)

    def test_citation_coverage_accepts_matching_statement_citations(self):
        from citation_coverage import (
            CitationCoverageClaim,
            CitationCoverageOutput,
            validate_coverage_claim_references,
        )
        from citation_support import extract_answer_statements

        statements = extract_answer_statements(
            "Registration Review takes 2 business days [1].",
            {1: "Registration Review takes 2 business days."},
        )

        output = CitationCoverageOutput(
            claims=[
                CitationCoverageClaim(
                    statement_id=1,
                    claim="Registration Review takes 2 business days.",
                    citation_ids=[1],
                )
            ]
        )

        validate_coverage_claim_references(output, statements)

    def test_citation_coverage_rejects_invented_citation(self):
        from citation_coverage import (
            CitationCoverageClaim,
            CitationCoverageOutput,
            validate_coverage_claim_references,
        )
        from citation_support import extract_answer_statements

        statements = extract_answer_statements(
            "Registration Review takes 2 business days.",
            {1: "Registration Review takes 2 business days."},
        )

        output = CitationCoverageOutput(
            claims=[
                CitationCoverageClaim(
                    statement_id=1,
                    claim="Registration Review takes 2 business days.",
                    citation_ids=[1],
                )
            ]
        )

        with self.assertRaises(ValueError):
            validate_coverage_claim_references(output, statements)

    def test_citation_coverage_rejects_unknown_statement_id(self):
        from citation_coverage import (
            CitationCoverageClaim,
            CitationCoverageOutput,
            validate_coverage_claim_references,
        )
        from citation_support import extract_answer_statements

        statements = extract_answer_statements(
            "Registration Review takes 2 business days [1].",
            {1: "Registration Review takes 2 business days."},
        )

        output = CitationCoverageOutput(
            claims=[
                CitationCoverageClaim(
                    statement_id=99,
                    claim="Registration Review takes 2 business days.",
                    citation_ids=[1],
                )
            ]
        )

        with self.assertRaises(ValueError):
            validate_coverage_claim_references(output, statements)

    def test_citation_coverage_normalizes_omitted_citations(self):
        from citation_coverage import (
            CitationCoverageClaim,
            CitationCoverageOutput,
            normalize_coverage_claim_citations,
            score_citation_coverage,
        )
        from citation_support import extract_answer_statements

        statements = extract_answer_statements(
            "Registration Review takes 2 business days [1].",
            {1: "Registration Review takes 2 business days."},
        )

        output = CitationCoverageOutput(
            claims=[
                CitationCoverageClaim(
                    statement_id=1,
                    claim="Registration Review takes 2 business days.",
                    citation_ids=[],
                )
            ]
        )

        normalized = normalize_coverage_claim_citations(output, statements)

        self.assertEqual(normalized.claims[0].citation_ids, [1])

        result = score_citation_coverage(
            normalized,
            {1: "Registration Review takes 2 business days."},
        )

        self.assertEqual(result["score"], 1.0)

    def test_citation_coverage_normalization_preserves_uncited_claims(self):
        from citation_coverage import (
            CitationCoverageClaim,
            CitationCoverageOutput,
            normalize_coverage_claim_citations,
            score_citation_coverage,
        )
        from citation_support import extract_answer_statements

        statements = extract_answer_statements(
            "Students can complete Registration Review online.",
            {1: "Registration Review takes 2 business days."},
        )

        output = CitationCoverageOutput(
            claims=[
                CitationCoverageClaim(
                    statement_id=1,
                    claim="Students can complete Registration Review online.",
                    citation_ids=[],
                )
            ]
        )

        normalized = normalize_coverage_claim_citations(output, statements)

        self.assertEqual(normalized.claims[0].citation_ids, [])

        result = score_citation_coverage(
            normalized,
            {1: "Registration Review takes 2 business days."},
        )

        self.assertEqual(result["score"], 0.0)

    def test_citation_coverage_normalization_rejects_invented_citations(self):
        from citation_coverage import (
            CitationCoverageClaim,
            CitationCoverageOutput,
            normalize_coverage_claim_citations,
        )
        from citation_support import extract_answer_statements

        statements = extract_answer_statements(
            "Students can complete Registration Review online.",
            {1: "Registration Review takes 2 business days."},
        )

        output = CitationCoverageOutput(
            claims=[
                CitationCoverageClaim(
                    statement_id=1,
                    claim="Students can complete Registration Review online.",
                    citation_ids=[1],
                )
            ]
        )

        with self.assertRaises(ValueError):
            normalize_coverage_claim_citations(output, statements)

    def test_citation_coverage_prompt_includes_cited_and_uncited_statements(self):
        from advanced_evaluation import build_citation_coverage_prompt
        from evaluation import EvaluationInput
        from unittest.mock import Mock

        item = Mock(spec=EvaluationInput)
        item.question = "How does Registration Review work?"
        item.actual_answer = (
            "Registration Review takes 2 business days [1]. "
            "Students can complete Registration Review online."
        )
        item.retrieved_evidence_by_rank = {
            1: "Registration Review takes 2 business days."
        }

        prompt = build_citation_coverage_prompt(item)

        self.assertIn(
            "Registration Review takes 2 business days [1].",
            prompt,
        )
        self.assertIn(
            "Students can complete Registration Review online.",
            prompt,
        )
        self.assertIn('"statement_id": 1', prompt)
        self.assertIn('"statement_id": 2', prompt)

    def test_citation_coverage_prompt_excludes_retrieved_evidence(self):
        from advanced_evaluation import build_citation_coverage_prompt
        from evaluation import EvaluationInput
        from unittest.mock import Mock

        item = Mock(spec=EvaluationInput)
        item.question = "How long does Registration Review take?"
        item.actual_answer = (
            "Registration Review takes 2 business days [1]."
        )
        item.retrieved_evidence_by_rank = {
            1: "UNIQUE_PRIVATE_RETRIEVED_EVIDENCE_MARKER"
        }

        prompt = build_citation_coverage_prompt(item)

        self.assertNotIn(
            "UNIQUE_PRIVATE_RETRIEVED_EVIDENCE_MARKER",
            prompt,
        )
        self.assertIn(
            "Return an empty citation_ids list",
            prompt,
        )

    def test_citation_coverage_provider_uses_structured_json(self):
        from advanced_evaluation import (
            generate_citation_coverage_with_gemini,
        )
        from citation_coverage import CitationCoverageOutput
        from unittest.mock import Mock, patch

        settings = Mock()
        settings.evaluator_provider = "gemini"
        settings.llm_api_key = "test-api-key"
        settings.evaluator_model = "gemini-test-model"
        settings.evaluator_temperature = 0.0

        parsed = CitationCoverageOutput.model_validate({
            "claims": [
                {
                    "statement_id": 1,
                    "claim": "Registration Review takes 2 business days.",
                    "citation_ids": [],
                }
            ],
            "summary": "One factual claim identified.",
            "reviewed_statement_ids": [1],
        })

        response = Mock()
        response.parsed = parsed
        response.text = parsed.model_dump_json()
        response.candidates = [Mock(finish_reason="STOP")]
        response.usage_metadata = Mock(
            prompt_token_count=150,
            candidates_token_count=75,
            total_token_count=225,
            thoughts_token_count=0,
        )

        with patch("advanced_evaluation.genai.Client") as client_class:
            client = client_class.return_value
            client.models.generate_content.return_value = response

            result = generate_citation_coverage_with_gemini(
                "Extract factual claims.",
                settings,
            )

            call_kwargs = client.models.generate_content.call_args.kwargs

            self.assertEqual(
                call_kwargs["config"].response_schema,
                CitationCoverageOutput,
            )
            self.assertEqual(
                call_kwargs["config"].response_mime_type,
                "application/json",
            )
            self.assertEqual(result.parsed.claims[0].statement_id, 1)
            self.assertEqual(result.input_tokens, 150)
            self.assertEqual(result.output_tokens, 75)
            self.assertEqual(result.total_tokens, 225)
            client.close.assert_called_once()

    def test_citation_coverage_provider_rejects_truncated_response(self):
        from advanced_evaluation import (
            generate_citation_coverage_with_gemini,
        )
        from unittest.mock import Mock, patch

        settings = Mock()
        settings.evaluator_provider = "gemini"
        settings.llm_api_key = "test-api-key"
        settings.evaluator_model = "gemini-test-model"
        settings.evaluator_temperature = 0.0

        response = Mock()
        response.candidates = [Mock(finish_reason="MAX_TOKENS")]

        with patch("advanced_evaluation.genai.Client") as client_class:
            client = client_class.return_value
            client.models.generate_content.return_value = response

            with self.assertRaises(RuntimeError):
                generate_citation_coverage_with_gemini(
                    "Extract factual claims.",
                    settings,
                )

            client.close.assert_called_once()

    def test_citation_coverage_statement_completeness_accepts_all_statements(self):
        from citation_coverage import (
            CitationCoverageClaim,
            CitationCoverageOutput,
            validate_coverage_statement_completeness,
        )

        output = CitationCoverageOutput(
            claims=[
                CitationCoverageClaim(
                    statement_id=1,
                    claim="Registration Review takes 2 business days.",
                    citation_ids=[],
                )
            ],
            reviewed_statement_ids=[1, 2],
        )

        result = validate_coverage_statement_completeness(output, 2)

        self.assertEqual(result["reviewed_statements"], 2)
        self.assertEqual(result["statement_review_coverage"], 1.0)

    def test_citation_coverage_statement_completeness_rejects_missing_statement(self):
        from citation_coverage import (
            CitationCoverageClaim,
            CitationCoverageOutput,
            validate_coverage_statement_completeness,
        )

        output = CitationCoverageOutput(
            claims=[
                CitationCoverageClaim(
                    statement_id=1,
                    claim="Registration Review takes 2 business days.",
                    citation_ids=[],
                )
            ],
            reviewed_statement_ids=[1],
        )

        with self.assertRaises(ValueError):
            validate_coverage_statement_completeness(output, 2)

    def test_citation_coverage_statement_completeness_rejects_duplicate_ids(self):
        from citation_coverage import (
            CitationCoverageOutput,
            validate_coverage_statement_completeness,
        )

        output = CitationCoverageOutput(
            claims=[],
            reviewed_statement_ids=[1, 1],
        )

        with self.assertRaises(ValueError):
            validate_coverage_statement_completeness(output, 1)

    def test_run_citation_coverage_with_mocked_provider(self):
        from advanced_evaluation import (
            ProviderExecution,
            run_citation_coverage,
        )
        from citation_coverage import (
            CitationCoverageClaim,
            CitationCoverageOutput,
        )
        from evaluation import EvaluationInput
        from unittest.mock import Mock

        item = Mock(spec=EvaluationInput)
        item.question = "How does Registration Review work?"
        item.actual_answer = (
            "Registration Review takes 2 business days [1]. "
            "Students can complete Registration Review online."
        )
        item.retrieved_evidence_by_rank = {
            1: "Registration Review takes 2 business days."
        }

        settings = Mock()
        settings.evaluator_provider = "gemini"
        settings.evaluator_model = "gemini-test-model"
        settings.evaluator_temperature = 0.0
        settings.evaluator_input_cost_per_million = 0.25
        settings.evaluator_output_cost_per_million = 1.50

        parsed = CitationCoverageOutput(
            claims=[
                CitationCoverageClaim(
                    statement_id=1,
                    claim="Registration Review takes 2 business days.",
                    citation_ids=[],
                ),
                CitationCoverageClaim(
                    statement_id=2,
                    claim="Students can complete Registration Review online.",
                    citation_ids=[],
                ),
            ],
            reviewed_statement_ids=[1, 2],
            summary="Two factual claims identified.",
        )

        def mock_provider(prompt, provider_settings):
            return ProviderExecution(
                parsed=parsed,
                raw_output=parsed.model_dump_json(),
                input_tokens=500,
                output_tokens=150,
                total_tokens=650,
                thinking_tokens=0,
                finish_reason="STOP",
            )

        execution = run_citation_coverage(
            item,
            settings,
            provider=mock_provider,
        )

        result = execution.result

        self.assertEqual(result.evaluator_key, "citation_coverage")
        self.assertEqual(result.normalized_score, 0.5)
        self.assertEqual(result.raw_score, 0.5)
        self.assertFalse(result.passed)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.details["total_claims"], 2)
        self.assertEqual(result.details["covered_claims"], 1)
        self.assertEqual(result.details["uncovered_claims"], 1)
        self.assertEqual(execution.total_tokens, 650)

    def test_run_citation_coverage_rejects_incomplete_statement_review(self):
        from advanced_evaluation import ProviderExecution, run_citation_coverage
        from citation_coverage import CitationCoverageOutput
        from evaluation import EvaluationInput
        from unittest.mock import Mock

        item = Mock(spec=EvaluationInput)
        item.question = "How does registration work?"
        item.actual_answer = (
            "Registration begins in March [1]. "
            "Students can register online."
        )
        item.retrieved_evidence_by_rank = {
            1: "Registration begins in March."
        }

        settings = Mock()

        parsed = CitationCoverageOutput(
            claims=[],
            reviewed_statement_ids=[1],
            summary="Incomplete review.",
        )

        def mock_provider(prompt, provider_settings):
            return ProviderExecution(
                parsed=parsed,
                raw_output=parsed.model_dump_json(),
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
            )

        with self.assertRaises(ValueError):
            run_citation_coverage(item, settings, provider=mock_provider)

    def test_run_citation_coverage_rejects_unexpected_provider_schema(self):
        from advanced_evaluation import ProviderExecution, run_citation_coverage
        from evaluation import EvaluationInput
        from unittest.mock import Mock

        item = Mock(spec=EvaluationInput)
        item.question = "When does registration begin?"
        item.actual_answer = "Registration begins in March [1]."
        item.retrieved_evidence_by_rank = {
            1: "Registration begins in March."
        }

        settings = Mock()

        def mock_provider(prompt, provider_settings):
            return ProviderExecution(
                parsed={"claims": []},
                raw_output='{"claims": []}',
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
            )

        with self.assertRaises(TypeError):
            run_citation_coverage(item, settings, provider=mock_provider)

    def test_run_citation_coverage_no_factual_claims_is_not_applicable(self):
        from advanced_evaluation import ProviderExecution, run_citation_coverage
        from citation_coverage import CitationCoverageOutput
        from evaluation import EvaluationInput
        from unittest.mock import Mock

        item = Mock(spec=EvaluationInput)
        item.question = "Can you help me?"
        item.actual_answer = "Hello! How can I help you?"
        item.retrieved_evidence_by_rank = {}

        settings = Mock()
        settings.evaluator_provider = "gemini"
        settings.evaluator_model = "gemini-test-model"
        settings.evaluator_temperature = 0.0
        settings.evaluator_input_cost_per_million = 0.25
        settings.evaluator_output_cost_per_million = 1.50

        parsed = CitationCoverageOutput(
            claims=[],
            reviewed_statement_ids=[1, 2],
            summary="No factual claims identified.",
        )

        def mock_provider(prompt, provider_settings):
            return ProviderExecution(
                parsed=parsed,
                raw_output=parsed.model_dump_json(),
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                thinking_tokens=0,
                finish_reason="STOP",
            )

        execution = run_citation_coverage(
            item,
            settings,
            provider=mock_provider,
        )

        result = execution.result

        self.assertIsNone(result.normalized_score)
        self.assertIsNone(result.raw_score)
        self.assertIsNone(result.passed)
        self.assertEqual(result.status, "skipped")
        self.assertEqual(result.details["total_claims"], 0)
        self.assertEqual(result.details["covered_claims"], 0)

    def test_engine_runs_citation_coverage_with_mocked_provider(self):
        from unittest.mock import Mock

        from advanced_evaluation import (
            AdvancedEvaluatorEngine,
            ProviderExecution,
        )
        from citation_coverage import (
            CitationCoverageClaim,
            CitationCoverageOutput,
        )
        from evaluation import EvaluationInput

        item = Mock(spec=EvaluationInput)
        item.question = "When does registration begin?"
        item.actual_answer = (
            "Registration begins in March [1]. "
            "Students can register online."
        )
        item.retrieved_evidence_by_rank = {
            1: "Registration begins in March."
        }

        settings = Mock()
        settings.evaluator_provider = "gemini"
        settings.evaluator_model = "gemini-test-model"
        settings.evaluator_temperature = 0.0
        settings.evaluator_input_cost_per_million = 0.25
        settings.evaluator_output_cost_per_million = 1.50

        parsed = CitationCoverageOutput(
            claims=[
                CitationCoverageClaim(
                    statement_id=1,
                    claim="Registration begins in March.",
                    citation_ids=[],
                ),
                CitationCoverageClaim(
                    statement_id=2,
                    claim="Students can register online.",
                    citation_ids=[],
                ),
            ],
            reviewed_statement_ids=[1, 2],
            summary="Two factual claims identified.",
        )

        provider = Mock(
            return_value=ProviderExecution(
                parsed=parsed,
                raw_output=parsed.model_dump_json(),
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                thinking_tokens=0,
                finish_reason="STOP",
            )
        )

        ragas_factory = Mock(
            side_effect=AssertionError(
                "Citation Coverage must not initialize RAGAS."
            )
        )

        with AdvancedEvaluatorEngine(
                settings,
                citation_coverage_provider=provider,
                ragas_factory=ragas_factory,
        ) as engine:
            execution = engine.run("citation_coverage", item)

        self.assertEqual(execution.result.status, "completed")
        self.assertEqual(execution.result.normalized_score, 0.5)
        self.assertEqual(execution.result.evaluator_key, "citation_coverage")
        self.assertEqual(execution.result.details["covered_claims"], 1)
        self.assertEqual(execution.result.details["total_claims"], 2)

        provider.assert_called_once()
        ragas_factory.assert_not_called()

    def test_citation_coverage_cli_executes_and_persists_with_mocks(self):
        from unittest.mock import MagicMock, patch

        from advanced_evaluation import AdvancedExecution
        from evaluation import EvaluationResult
        from run_advanced_evaluation import execute_plan

        settings = MagicMock()

        preflight = {
            "paid_application_count": 1,
            "estimated_cost": 0.0075,
            "applications": [
                {
                    "response_id": 158,
                    "evaluator": "citation_coverage",
                    "action": "run",
                    "attempts": 1,
                }
            ],
        }

        item = MagicMock()
        item.actual_answer = (
            "Registration Review takes 2 business days [1]. "
            "Advising appointments are available online."
        )
        item.retrieved_evidence_by_rank = {
            1: "Registration Review takes 2 business days."
        }

        result = EvaluationResult(
            evaluator_key="citation_coverage",
            raw_score=0.5,
            normalized_score=0.5,
            passed=False,
            explanation="One of two factual claims has a valid citation.",
            details={
                "total_claims": 2,
                "covered_claims": 1,
                "uncovered_claims": 1,
            },
            runtime_ms=12,
            status="completed",
            configuration={
                "provider": "gemini",
                "model": "mock-model",
            },
            estimated_cost=0.0002,
        )

        execution = AdvancedExecution(
            result=result,
            raw_provider_output='{"claims":[]}',
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            thinking_tokens=0,
        )

        mock_connection = MagicMock()
        mock_engine = MagicMock()
        mock_engine.run.return_value = execution

        mock_engine_context = MagicMock()
        mock_engine_context.__enter__.return_value = mock_engine

        with (
            patch(
                "run_advanced_evaluation.AdvancedEvaluatorEngine",
                return_value=mock_engine_context,
            ),
            patch(
                "run_advanced_evaluation.database_connection",
            ) as mock_database,
            patch(
                "run_advanced_evaluation.load_evaluation_input",
                return_value=item,
            ) as mock_load,
            patch(
                "run_advanced_evaluation.persist_result",
                return_value=1,
            ) as mock_persist,
            patch(
                "run_advanced_evaluation.active_evaluator",
                return_value={"evaluator_id": 30},
            ) as mock_active,
        ):
            mock_database.return_value.__enter__.return_value = mock_connection

            outcomes = execute_plan(
                settings,
                preflight,
                allow_paid=True,
                allow_unknown_cost=False,
            )

        mock_active.assert_called_once_with(
            mock_connection,
            "citation_coverage",
        )

        mock_load.assert_called_once_with(
            mock_connection,
            158,
            require_expected_answer=False,
        )

        mock_engine.run.assert_called_once_with(
            "citation_coverage",
            item,
        )

        mock_persist.assert_called_once_with(
            mock_connection,
            response_id=158,
            result=result,
            raw_provider_output=execution.raw_provider_output,
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )

        mock_connection.start_transaction.assert_called_once()
        mock_connection.commit.assert_called_once()
        mock_connection.rollback.assert_not_called()

        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0]["response_id"], 158)
        self.assertEqual(outcomes[0]["evaluator"], "citation_coverage")
        self.assertEqual(outcomes[0]["attempt_number"], 1)
        self.assertEqual(outcomes[0]["result"]["normalized_score"], 0.5)
        self.assertEqual(outcomes[0]["result"]["status"], "completed")
        self.assertEqual(outcomes[0]["usage"]["total_tokens"], 150)

if __name__ == "__main__":
    unittest.main()
