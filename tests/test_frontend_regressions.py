"""Static regression checks for high-impact browser rendering mistakes."""

from pathlib import Path
import re
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FrontendRegressionTests(unittest.TestCase):
    def test_app_does_not_treat_html_tag_selectors_as_new_elements(self) -> None:
        javascript = (PROJECT_ROOT / "assets" / "js" / "app.js").read_text(encoding="utf-8")
        selector_used_as_constructor = re.compile(
            r'\$\("(?:article|button|div|p|small|span|strong)"\)\s*\.(?:addClass|text)'
        )

        self.assertIsNone(
            selector_used_as_constructor.search(javascript),
            "Use $('<tag>') to create an element; $('tag') selects and can move the existing page DOM.",
        )

    def test_results_separate_method_families_statuses_and_score_contracts(self) -> None:
        javascript = (PROJECT_ROOT / "assets" / "js" / "app.js").read_text(encoding="utf-8")
        for phrase in (
            "Local metrics",
            "LLM judge",
            "RAGAS metrics",
            "Human review · supporting evidence",
            "completed",
            "failed",
            "skipped",
            "What this score means",
            "No threshold; inspect the value directly.",
        ):
            self.assertIn(phrase, javascript)

        api = (PROJECT_ROOT / "api" / "evaluations.php").read_text(encoding="utf-8")
        for field in (
            "completed_result_count",
            "local_completed_count",
            "judge_completed_count",
            "ragas_completed_count",
        ):
            self.assertIn(field, api)

    def test_frontend_does_not_combine_unlike_metrics(self) -> None:
        frontend = "\n".join(
            (PROJECT_ROOT / path).read_text(encoding="utf-8")
            for path in ("assets/js/app.js", "index.php", "api/evaluations.php")
        ).lower()
        self.assertNotIn("descriptive_average", frontend)
        self.assertNotIn("overall metric average", frontend)
        self.assertIn("do not combine unlike scores", frontend)

    def test_findings_require_question_matched_baseline_pairs(self) -> None:
        api = (PROJECT_ROOT / "api" / "evaluations.php").read_text(encoding="utf-8")
        javascript = (PROJECT_ROOT / "assets" / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn("baseline_response.question_id=comparison_response.question_id", api)
        self.assertIn("matched_comparisons", api)
        self.assertIn("No valid paired comparison exists yet.", javascript)

    def test_web_generation_is_disabled_without_explicit_environment_flag(self) -> None:
        ask_api = (PROJECT_ROOT / "api" / "ask.php").read_text(encoding="utf-8")
        self.assertIn("ALLOW_PAID_GENERATION", ask_api)
        self.assertIn("--allow-paid", ask_api)

    def test_chat_settings_are_visible_validated_and_forwarded(self) -> None:
        index = (PROJECT_ROOT / "index.php").read_text(encoding="utf-8")
        javascript = (PROJECT_ROOT / "assets" / "js" / "app.js").read_text(encoding="utf-8")
        ask_api = (PROJECT_ROOT / "api" / "ask.php").read_text(encoding="utf-8")

        for control_id in (
            "chatModel",
            "chatRetrievalMethod",
            "chatTopK",
            "chatTemperature",
            "chatTopP",
            "previewSourcesButton",
        ):
            self.assertIn(control_id, index)
            self.assertIn(control_id, javascript)
        for command_flag in ("--model", "--retrieval", "--top-k", "--temperature", "--top-p", "--dry-run"):
            self.assertIn(command_flag, ask_api)
        self.assertIn("between 0.0 and 1.0", ask_api)
        self.assertIn("LLM_CHAT_MODELS", ask_api)

        evaluations_api = (PROJECT_ROOT / "api" / "evaluations.php").read_text(encoding="utf-8")
        self.assertIn("settings.temperature", evaluations_api)
        self.assertIn("settings.top_p", evaluations_api)

    def test_evaluation_and_results_explain_their_different_jobs(self) -> None:
        index = (PROJECT_ROOT / "index.php").read_text(encoding="utf-8")
        navigation = (PROJECT_ROOT / "includes" / "nav.php").read_text(encoding="utf-8")
        javascript = (PROJECT_ROOT / "assets" / "js" / "app.js").read_text(encoding="utf-8")
        health_api = (PROJECT_ROOT / "api" / "health.php").read_text(encoding="utf-8")
        ask_api = (PROJECT_ROOT / "api" / "ask.php").read_text(encoding="utf-8")
        self.assertIn("This is the gold standard—not chat history", index)
        self.assertIn("This page reviews the questions—it does not call the model", index)
        self.assertIn("same retrieval-and-answer code used by Chat", index)
        self.assertIn("Chat and evaluation runs use the same retrieval-and-answer pipeline", index)
        self.assertIn("Evaluation scores answers that are already saved", index)
        self.assertIn("1. Choose a saved test · 2. Score missing methods", index)
        self.assertIn("Gold Standard", navigation)
        self.assertIn(">Evaluation<", navigation)
        self.assertIn("applicationStatusPill", index)
        self.assertIn("api/health.php", javascript)
        self.assertIn("Application data unavailable", javascript)
        self.assertNotIn("Verify the local database setup", javascript)
        self.assertIn("contact the application administrator", health_api)
        self.assertIn("Try again or contact the application administrator", ask_api)
        self.assertNotIn("Check the server configuration", ask_api)

    def test_frontend_can_administer_the_active_index(self) -> None:
        index = (PROJECT_ROOT / "index.php").read_text(encoding="utf-8")
        javascript = (PROJECT_ROOT / "assets" / "js" / "app.js").read_text(encoding="utf-8")
        documents_api = (PROJECT_ROOT / "api" / "documents.php").read_text(encoding="utf-8")
        admin = (PROJECT_ROOT / "rag" / "admin.py").read_text(encoding="utf-8")
        for control_id in (
            "overviewChunkCount",
            "documentSearch",
            "documentCategoryFilter",
            "documentTypeFilter",
            "documentSort",
            "restoreBundledDocumentsButton",
            "deleteAllDocumentsButton",
            "duplicateDocumentPrompt",
            "confirmDuplicateReplacement",
            "cancelDuplicateUpload",
        ):
            self.assertIn(control_id, index)
            self.assertIn(control_id, javascript)
        self.assertIn("DELETE ALL", javascript)
        self.assertIn("restore_bundled", javascript)
        self.assertIn("runBundledDocumentRestore", documents_api)
        self.assertIn("rag/ingest.py", documents_api)
        self.assertIn("original_filename = ?", documents_api)
        self.assertIn("documentJsonPayload", documents_api)
        self.assertIn("uploadedStoragePath", documents_api)
        self.assertIn("Document operation failed. Try again or contact the application administrator.", documents_api)
        self.assertNotIn("documentResponse(500, ['ok' => false, 'error' => $error->getMessage()])", documents_api)
        self.assertIn("--delete-all", admin)
        self.assertIn("Replace existing", index)
        self.assertIn("delete_source_chunks", admin)
        self.assertIn("Vector cleanup verification failed", (PROJECT_ROOT / "rag" / "vector_store.py").read_text(encoding="utf-8"))
        self.assertGreaterEqual(javascript.count("resetAnswer();"), 4)
        self.assertNotIn("Only browser-uploaded documents can be deleted", admin)

    def test_saved_runs_have_a_browser_evaluation_workflow(self) -> None:
        index = (PROJECT_ROOT / "index.php").read_text(encoding="utf-8")
        javascript = (PROJECT_ROOT / "assets" / "js" / "app.js").read_text(encoding="utf-8")
        endpoint = (PROJECT_ROOT / "api" / "run_evaluation.php").read_text(encoding="utf-8")
        runner = (PROJECT_ROOT / "rag" / "evaluate_saved_run.py").read_text(encoding="utf-8")
        evaluations_api = (PROJECT_ROOT / "api" / "evaluations.php").read_text(encoding="utf-8")
        self.assertIn("Score and inspect saved answers", index)
        self.assertIn("evaluate-run-toggle", javascript)
        self.assertIn("evaluate-response-button", javascript)
        self.assertIn("Check what will run", javascript)
        self.assertIn("Metric averages for this test and all tests", javascript)
        self.assertIn("api/run_evaluation.php", javascript)
        self.assertIn("ALLOW_PAID_EVALUATION", endpoint)
        self.assertIn("runEvaluationUserError", endpoint)
        self.assertIn("Request body must contain valid JSON.", endpoint)
        self.assertIn("response_id", endpoint)
        self.assertIn("--response-id", runner)
        self.assertIn("LOCAL_EVALUATOR_KEYS", runner)
        self.assertIn("AVG(CASE WHEN result.status='completed'", evaluations_api)
        self.assertIn("all_runs_mean", evaluations_api)
        self.assertIn("This answer", javascript)
        self.assertIn("Completed tests", javascript)

    def test_saved_runs_can_export_portable_json_and_csv_evidence(self) -> None:
        javascript = (PROJECT_ROOT / "assets" / "js" / "app.js").read_text(encoding="utf-8")
        endpoint = (PROJECT_ROOT / "api" / "exports.php").read_text(encoding="utf-8")

        self.assertIn("Export JSON", javascript)
        self.assertIn("Export CSV", javascript)
        self.assertIn("api/exports.php?run_id=", javascript)
        self.assertIn("EXPORT_SCHEMA_VERSION", endpoint)
        self.assertIn("evaluation_snapshot_json", endpoint)
        self.assertIn("evaluator_result_attempts", endpoint)
        self.assertIn("matched_comparisons", endpoint)
        self.assertIn("fputcsv", endpoint)

    def test_frontend_can_preview_and_create_bounded_test_runs(self) -> None:
        index = (PROJECT_ROOT / "index.php").read_text(encoding="utf-8")
        javascript = (PROJECT_ROOT / "assets" / "js" / "app.js").read_text(encoding="utf-8")
        endpoint = (PROJECT_ROOT / "api" / "test_runs.php").read_text(encoding="utf-8")
        runner = (PROJECT_ROOT / "rag" / "run_evaluation.py").read_text(encoding="utf-8")

        for control_id in (
            "newTestRunToggle",
            "newTestName",
            "newTestLimit",
            "newTestQuestionIds",
            "newTestModel",
            "newTestRetrieval",
            "newTestTopK",
            "newTestTemperature",
            "newTestTopP",
            "previewNewTestRun",
            "createNewTestRun",
        ):
            self.assertIn(control_id, index)
            self.assertIn(control_id, javascript)
        self.assertIn("api/test_runs.php", javascript)
        self.assertIn("ALLOW_PAID_GENERATION", endpoint)
        self.assertIn("Request body must contain valid JSON.", endpoint)
        self.assertIn("contact the application administrator", endpoint)
        self.assertIn("MAX_TEST_RUN_RESPONSES", endpoint)
        for command_flag in ("--model", "--temperature", "--top-p", "--question-ids", "--dry-run"):
            self.assertIn(command_flag, endpoint)
            self.assertIn(command_flag, runner)
        self.assertIn("question_ids", javascript)
        self.assertIn("exact ordered reviewed-question", javascript)
        self.assertIn("Current index:", index)
        self.assertIn("requires rebuilding a separate index", index)

    def test_browser_guides_one_variable_baseline_comparisons(self) -> None:
        index = (PROJECT_ROOT / "index.php").read_text(encoding="utf-8")
        javascript = (PROJECT_ROOT / "assets" / "js" / "app.js").read_text(encoding="utf-8")
        endpoint = (PROJECT_ROOT / "api" / "test_runs.php").read_text(encoding="utf-8")
        runner = (PROJECT_ROOT / "rag" / "run_evaluation.py").read_text(encoding="utf-8")

        for control_id in (
            "newTestExperimentMode",
            "newTestBaselineRun",
            "newTestExperimentKey",
            "newTestControlledVariable",
            "newTestCorpusScope",
            "newTestCategoryChoices",
            "newTestBaselineSummary",
            "researchReadinessList",
        ):
            self.assertIn(control_id, index)
            self.assertIn(control_id, javascript)
        self.assertIn("Compare with a saved baseline", index)
        self.assertIn("change exactly one setting", index.lower())
        self.assertIn("The form copies and locks the other settings", javascript)
        self.assertIn("newTestValidationError", javascript)
        self.assertIn("renderResearchReadiness", javascript)
        self.assertIn("What still needs evidence?", index)
        for command_flag in (
            "--experiment-key",
            "--baseline-run-id",
            "--change-from-baseline",
            "--corpus-variant",
            "--categories",
        ):
            self.assertIn(command_flag, endpoint)
            self.assertIn(command_flag, runner)
        self.assertIn("controlled_differences", runner)
        self.assertIn("must change exactly one supported setting", runner)
        self.assertIn("exact ordered reviewed-question", runner)

    def test_evaluation_uses_user_facing_question_labels_and_actionable_history(self) -> None:
        javascript = (PROJECT_ROOT / "assets" / "js" / "app.js").read_text(encoding="utf-8")
        api = (PROJECT_ROOT / "api" / "evaluations.php").read_text(encoding="utf-8")

        self.assertIn("Question \" + questionNumber + \" of", javascript)
        self.assertIn("Earlier attempts needing attention", javascript)
        self.assertIn('attentionRunCount === 1 ? " needs" : "s need"', javascript)
        self.assertIn("Use Score saved answers to add the missing checks", javascript)
        self.assertNotIn("This setup attempt failed", javascript)
        self.assertNotIn('text("Response " + response.response_id', javascript)
        self.assertIn("run_question_number", api)
        self.assertIn("dataset_question_number", api)

    def test_metric_dependencies_are_explicit(self) -> None:
        index = (PROJECT_ROOT / "index.php").read_text(encoding="utf-8")
        javascript = (PROJECT_ROOT / "assets" / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn("Needs gold-standard data", index)
        self.assertIn("No gold answer required", index)
        self.assertIn("none of them finds or generates the answer", index)
        self.assertIn("ragas_faithfulness", javascript)
        self.assertIn("needs gold standard", javascript)


if __name__ == "__main__":
    unittest.main()
