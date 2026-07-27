"""Unit tests for deterministic, provider-free RAG helper behavior."""

from __future__ import annotations

import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "rag"))

from answer import answer_question  # noqa: E402
from document_loader import DocumentLoadError, load_document  # noqa: E402
from evaluation import (  # noqa: E402
    EvaluationInput,
    exact_contains,
    expected_source_accuracy,
    normalize_text,
    refusal_correctness,
    required_fact_coverage,
    rouge_l,
    token_f1,
    run_evaluator,
    LOCAL_EVALUATORS,
)
from ingest import build_loaded_document_chunks, chunk_text, stable_chroma_id  # noqa: E402
from llm import (  # noqa: E402
    REFUSAL_MESSAGE,
    SYSTEM_INSTRUCTION,
    GenerationExecution,
    build_grounded_prompt,
    estimate_generation_cost,
    estimated_generation_application_cost,
    generate_with_gemini,
)
from query import SearchResult, lexical_score, retrieval_provenance  # noqa: E402
from run_evaluation import evaluation_snapshot  # noqa: E402
from provenance import code_provenance  # noqa: E402
from settings import load_settings  # noqa: E402
from vector_store import delete_source_chunks  # noqa: E402


class FakeVectorCollection:
    def __init__(self, records: dict[str, str], *, ignore_deletes: bool = False) -> None:
        self.records = records.copy()
        self.ignore_deletes = ignore_deletes

    def get(self, *, where: dict[str, str] | None = None, include: list[str] | None = None) -> dict[str, list[str]]:
        del include
        ids = list(self.records)
        if where:
            ids = [item_id for item_id in ids if self.records[item_id] == where["source_path"]]
        return {"ids": ids}

    def delete(self, *, ids: list[str]) -> None:
        if self.ignore_deletes:
            return
        for item_id in ids:
            self.records.pop(item_id, None)


class VectorCleanupTests(unittest.TestCase):
    def test_delete_source_chunks_removes_only_the_selected_document(self) -> None:
        collection = FakeVectorCollection({"old-1": "old.txt", "old-2": "old.txt", "keep": "keep.txt"})

        deleted = delete_source_chunks(collection, "old.txt")

        self.assertEqual(2, deleted)
        self.assertEqual({"keep": "keep.txt"}, collection.records)

    def test_delete_source_chunks_detects_a_stale_preview_risk(self) -> None:
        collection = FakeVectorCollection({"old-1": "old.txt"}, ignore_deletes=True)

        with self.assertRaisesRegex(RuntimeError, "old chunks remain"):
            delete_source_chunks(collection, "old.txt")


class ChunkTextTests(unittest.TestCase):
    def test_empty_text_produces_no_chunks(self) -> None:
        self.assertEqual([], chunk_text("  \n\t", chunk_size=20, overlap=5))

    def test_overlap_is_preserved(self) -> None:
        self.assertEqual(
            ["abcdefghij", "hijklmnopq", "opqrstuvwx", "vwxyz"],
            chunk_text("abcdefghijklmnopqrstuvwxyz", chunk_size=10, overlap=3),
        )

    def test_invalid_overlap_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            chunk_text("text", chunk_size=10, overlap=10)


class StableIdTests(unittest.TestCase):
    def test_same_path_and_index_produce_same_id(self) -> None:
        first = stable_chroma_id("data/example.txt", 3)
        second = stable_chroma_id("data/example.txt", 3)
        self.assertEqual(first, second)

    def test_chunk_index_changes_id(self) -> None:
        self.assertNotEqual(
            stable_chroma_id("data/example.txt", 2),
            stable_chroma_id("data/example.txt", 3),
        )


class DocumentLoaderTests(unittest.TestCase):
    def test_utf8_txt_is_loaded_with_safe_original_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stored.txt"
            path.write_text("Metro State registration details", encoding="utf-8-sig")
            loaded = load_document(path, original_filename="../Registration.txt")

        self.assertEqual("txt", loaded.source_type)
        self.assertEqual("Registration.txt", loaded.original_filename)
        self.assertIn("registration details", loaded.text)

    def test_binary_txt_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.txt"
            path.write_bytes(b"text\x00binary")
            with self.assertRaisesRegex(DocumentLoadError, "binary data"):
                load_document(path)

    def test_empty_pdf_is_rejected_as_non_extractable(self) -> None:
        fake_reader = SimpleNamespace(is_encrypted=False, pages=[SimpleNamespace(extract_text=lambda: "")])
        fake_module = SimpleNamespace(PdfReader=lambda _path: fake_reader)
        with tempfile.TemporaryDirectory() as directory, patch.dict(sys.modules, {"pypdf": fake_module}):
            path = Path(directory) / "scan.pdf"
            path.write_bytes(b"%PDF fixture")
            with self.assertRaisesRegex(DocumentLoadError, "require OCR"):
                load_document(path)

    def test_pdf_text_is_extracted(self) -> None:
        fake_reader = SimpleNamespace(
            is_encrypted=False,
            pages=[SimpleNamespace(extract_text=lambda: "Financial aid deadline")],
        )
        fake_module = SimpleNamespace(PdfReader=lambda _path: fake_reader)
        with tempfile.TemporaryDirectory() as directory, patch.dict(sys.modules, {"pypdf": fake_module}):
            path = Path(directory) / "aid.pdf"
            path.write_bytes(b"%PDF fixture")
            loaded = load_document(path)
        self.assertEqual("pdf", loaded.source_type)
        self.assertEqual("Financial aid deadline", loaded.text)

    def test_docx_paragraph_and_table_are_extracted(self) -> None:
        from docx import Document

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "support.docx"
            document = Document()
            document.add_paragraph("Student support services")
            table = document.add_table(rows=1, cols=2)
            table.cell(0, 0).text = "Office"
            table.cell(0, 1).text = "Library"
            document.save(path)
            loaded = load_document(path)

        self.assertIn("Student support services", loaded.text)
        self.assertIn("Office\tLibrary", loaded.text)

    def test_loaded_metadata_is_preserved_in_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.txt"
            path.write_text("A policy statement long enough for two chunks.", encoding="utf-8")
            loaded = load_document(path, original_filename="Policy.txt")
            chunks = build_loaded_document_chunks(
                loaded,
                source_path="storage/uploads/id.txt",
                category="policies",
                chunk_size=30,
                overlap=5,
            )

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk.source_type == "txt" for chunk in chunks))
        self.assertTrue(all(chunk.original_filename == "Policy.txt" for chunk in chunks))


class LexicalScoreTests(unittest.TestCase):
    def test_exact_answer_phrase_scores_above_partial_match(self) -> None:
        question = "When does Fall 2026 registration begin?"
        exact = "Fall 2026 registration begins in eServices on March 23."
        partial = "Fall visiting student registration opens in June 2026."
        self.assertGreater(lexical_score(question, exact), lexical_score(question, partial))

    def test_retrieval_contract_documents_score_direction_and_version(self) -> None:
        contract = retrieval_provenance("chroma_vector")
        self.assertEqual("lower_is_better", contract["score_direction"])
        self.assertTrue(contract["version"])
        self.assertIn("semantic_distance", contract["final_score"])


def sample_context() -> SearchResult:
    return SearchResult(
        rank=1,
        source_path="data/metrostate_documents/academic_calendar/fall_2026.txt",
        category="academic_calendar",
        chunk_index=0,
        text="Fall 2026 registration begins in eServices Monday, March 23, 2026.",
        distance=0.5,
        keyword_score=10,
        document_id=2,
        chunk_id=10,
    )


class GroundedAnswerTests(unittest.TestCase):
    def test_prompt_contains_question_and_source_metadata(self) -> None:
        prompt = build_grounded_prompt("When does registration begin?", [sample_context()])
        self.assertIn("When does registration begin?", prompt)
        self.assertIn("fall_2026.txt", prompt)
        self.assertIn("March 23, 2026", prompt)

    def test_system_instruction_requires_exact_refusal(self) -> None:
        self.assertIn(REFUSAL_MESSAGE, SYSTEM_INSTRUCTION)
        self.assertIn("only the supplied source excerpts", SYSTEM_INSTRUCTION)

    def test_answer_workflow_accepts_injected_generator(self) -> None:
        def fake_generator(prompt: str, _settings: object) -> str:
            self.assertIn("March 23, 2026", prompt)
            return "Registration begins March 23, 2026."

        with patch("answer.semantic_search", return_value=[sample_context()]):
            result = answer_question(
                "When does Fall 2026 registration begin?",
                top_k=1,
                save=False,
                generator=fake_generator,
            )

        self.assertEqual("Registration begins March 23, 2026.", result.answer)
        self.assertEqual(1, len(result.sources))
        self.assertIsNone(result.response_id)

    def test_answer_workflow_applies_browser_generation_settings(self) -> None:
        observed_settings = []

        def fake_generator(_prompt: str, settings: object) -> str:
            observed_settings.append(settings)
            return "Grounded answer."

        with patch("answer.semantic_search", return_value=[sample_context()]):
            result = answer_question(
                "When does registration begin?",
                top_k=5,
                save=False,
                generator=fake_generator,
                temperature=0.5,
                top_p=0.7,
                model="gemini-2.5-flash-lite",
            )

        self.assertEqual("gemini-2.5-flash-lite", result.model)
        self.assertEqual(0.5, result.temperature)
        self.assertEqual(0.7, result.top_p)
        self.assertEqual(0.5, observed_settings[0].llm_temperature)
        self.assertEqual(0.7, observed_settings[0].llm_top_p)
        self.assertEqual("gemini-2.5-flash-lite", observed_settings[0].llm_chat_model)

    def test_answer_workflow_rejects_out_of_range_generation_settings(self) -> None:
        with self.assertRaisesRegex(ValueError, "temperature must be between"):
            answer_question(
                "When does registration begin?",
                top_k=1,
                save=False,
                temperature=1.1,
            )

    def test_answer_workflow_records_provider_usage_without_inventing_cost(self) -> None:
        def fake_generator(_prompt: str, _settings: object) -> GenerationExecution:
            return GenerationExecution("Grounded answer.", 100, 20, 120)

        unpriced = replace(
            load_settings(),
            llm_input_cost_per_million=0.0,
            llm_output_cost_per_million=0.0,
        )
        with (
            patch("answer.semantic_search", return_value=[sample_context()]),
            patch("answer.load_settings", return_value=unpriced),
        ):
            result = answer_question(
                "When does registration begin?",
                top_k=1,
                save=False,
                generator=fake_generator,
            )

        self.assertEqual(120, result.total_tokens)
        self.assertIsNone(result.estimated_cost)
        self.assertEqual("unavailable", result.generation_cost_status)

    def test_generation_cost_is_unknown_until_pricing_is_configured(self) -> None:
        settings = load_settings()
        unpriced = replace(
            settings,
            llm_input_cost_per_million=0.0,
            llm_output_cost_per_million=0.0,
        )
        priced = replace(
            settings,
            llm_input_cost_per_million=1.0,
            llm_output_cost_per_million=2.0,
        )
        self.assertIsNone(estimate_generation_cost(100, 20, unpriced))
        self.assertIsNone(estimated_generation_application_cost(unpriced))
        self.assertEqual(0.00014, estimate_generation_cost(100, 20, priced))
        self.assertEqual(0.007024, estimated_generation_application_cost(priced))

    def test_gemini_requires_api_key(self) -> None:
        settings = replace(load_settings(), llm_api_key="")
        with self.assertRaisesRegex(RuntimeError, "API key is not configured"):
            generate_with_gemini("prompt", settings)


def sample_evaluation_input(**overrides: object) -> EvaluationInput:
    values = {
        "response_id": 7,
        "question": "When does Fall 2026 registration begin?",
        "expected_answer": "Fall 2026 registration begins Monday, March 23, 2026.",
        "actual_answer": "Registration begins on Monday, March 23, 2026.",
        "expected_source": "data/metrostate_documents/academic_calendar/fall_2026.txt",
        "retrieved_sources": ["data/metrostate_documents/academic_calendar/fall_2026.txt"],
        "accepted_answers": ["March 23, 2026"],
        "required_facts": ["March 23, 2026"],
        "is_answerable": True,
    }
    values.update(overrides)
    return EvaluationInput(**values)  # type: ignore[arg-type]


class LocalEvaluatorTests(unittest.TestCase):
    def test_normalization_ignores_case_and_punctuation(self) -> None:
        self.assertEqual("march 23 2026", normalize_text("March 23, 2026!"))

    def test_exact_contains_accepts_reviewed_variant(self) -> None:
        score, passed, _explanation, details = exact_contains(sample_evaluation_input())
        self.assertTrue(passed)
        self.assertEqual(0.75, score)
        self.assertTrue(details["contains"])

    def test_required_fact_coverage_reports_missing_facts(self) -> None:
        score, passed, _explanation, details = required_fact_coverage(
            sample_evaluation_input(required_facts=["March 23, 2026", "eServices"])
        )
        self.assertEqual(0.5, score)
        self.assertFalse(passed)
        self.assertEqual(["eServices"], details["missing"])

    def test_token_f1_is_bounded(self) -> None:
        score, _passed, _explanation, details = token_f1(sample_evaluation_input())
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)
        self.assertLessEqual(details["precision"], 1.0)

    def test_rouge_l_uses_ordered_common_sequence(self) -> None:
        score, passed, _explanation, details = rouge_l(sample_evaluation_input())
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)
        self.assertTrue(passed)
        self.assertGreater(details["lcs_tokens"], 0)

    def test_expected_source_accuracy_records_rank(self) -> None:
        score, passed, _explanation, details = expected_source_accuracy(sample_evaluation_input())
        self.assertEqual(1.0, score)
        self.assertTrue(passed)
        self.assertEqual(1, details["retrieved_rank"])

    def test_refusal_correctness_uses_answerability_label(self) -> None:
        item = sample_evaluation_input(
            expected_answer=REFUSAL_MESSAGE,
            actual_answer=REFUSAL_MESSAGE,
            expected_source=None,
            retrieved_sources=[],
            accepted_answers=[REFUSAL_MESSAGE],
            required_facts=[],
            is_answerable=False,
        )
        score, passed, _explanation, details = refusal_correctness(item)
        self.assertEqual(1.0, score)
        self.assertTrue(passed)
        self.assertTrue(details["returned_fixed_refusal"])

    def test_evaluator_failure_is_returned_as_a_result(self) -> None:
        def failing_evaluator(_item: EvaluationInput) -> object:
            raise RuntimeError("controlled evaluator failure")

        with patch.dict(LOCAL_EVALUATORS, {"failing": failing_evaluator}):
            result = run_evaluator("failing", sample_evaluation_input())

        self.assertEqual("failed", result.status)
        self.assertIn("controlled evaluator failure", result.error_message or "")
        self.assertIsNone(result.normalized_score)


class EvaluationSnapshotTests(unittest.TestCase):
    def test_snapshot_freezes_reviewed_answer_key_and_dataset_version(self) -> None:
        question = {
            "question_id": 9,
            "question_key": "registration-date",
            "question_text": "When?",
            "expected_answer": "April 6, 2026",
            "expected_source": "summer_2026.txt",
            "expected_evidence": "Open registration",
            "accepted_answers": '["April 6, 2026"]',
            "required_facts": '["April 6, 2026"]',
            "category": "calendar",
            "difficulty": "easy",
            "is_answerable": 1,
            "review_status": "reviewed",
            "updated_at": "2026-07-20 12:00:00",
        }
        dataset = {"dataset_id": 2, "dataset_name": "Capstone", "version": "1.2"}
        snapshot = evaluation_snapshot(question, dataset)
        question["expected_answer"] = "mutated later"

        self.assertEqual("April 6, 2026", snapshot["expected_answer"])
        self.assertEqual(["April 6, 2026"], snapshot["required_facts"])
        self.assertEqual("1.2", snapshot["dataset_version"])

    def test_code_provenance_includes_runtime_and_dependency_versions(self) -> None:
        provenance = code_provenance()
        self.assertTrue(provenance["source_tree_sha256"])
        self.assertTrue(provenance["python_version"])
        self.assertIn("google-genai", provenance["dependencies"])


if __name__ == "__main__":
    unittest.main()
