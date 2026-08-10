from __future__ import annotations

import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = PROJECT_ROOT / "data" / "evaluation" / "final-study"
EXPECTED_RUN_IDS = [5, 6, 7, 8, 10, 12]
EXPECTED_QUESTION_IDS = [1, 23, 210, 213, 221]


class RepositoryEvidenceTests(unittest.TestCase):
    def load_exports(self) -> list[dict]:
        exports = []
        for run_id in EXPECTED_RUN_IDS:
            path = EVIDENCE_ROOT / f"final-study-run-{run_id}.json"
            self.assertTrue(path.is_file(), f"Missing final-study export: {path.name}")
            exports.append(json.loads(path.read_text(encoding="utf-8")))
        return exports

    def test_exports_cover_six_completed_exact_question_conditions(self) -> None:
        exports = self.load_exports()
        self.assertEqual(
            [int(export["run"]["run_id"]) for export in exports],
            EXPECTED_RUN_IDS,
        )
        for export in exports:
            self.assertEqual(export["run"]["status"], "completed")
            self.assertEqual(len(export["responses"]), 5)
            self.assertEqual(
                [int(response["question_id"]) for response in export["responses"]],
                EXPECTED_QUESTION_IDS,
            )

    def test_export_totals_match_the_public_final_report(self) -> None:
        exports = self.load_exports()
        responses = [response for export in exports for response in export["responses"]]
        results = [result for response in responses for result in response["results"]]
        current_reviews = [
            review
            for response in responses
            for review in response["human_reviews"]
            if review["is_current"]
        ]

        self.assertEqual(len(responses), 30)
        self.assertEqual(len(results), 250)
        self.assertEqual(sum(result["status"] == "completed" for result in results), 238)
        self.assertEqual(sum(result["status"] == "skipped" for result in results), 12)
        self.assertEqual(sum(not result["is_local"] for result in results), 10)
        self.assertEqual(len(current_reviews), 7)

    def test_exports_exclude_secrets_and_machine_local_paths(self) -> None:
        blocked_markers = (
            "GEMINI_API_KEY",
            "LLM_API_KEY",
            "DB_PASSWORD",
            "AIza",
            "C:\\Users\\",
            ".local-notes",
            "mysql-data",
        )
        for path in sorted(EVIDENCE_ROOT.glob("final-study-run-*.json")):
            contents = path.read_text(encoding="utf-8")
            for marker in blocked_markers:
                self.assertNotIn(marker, contents, f"{marker!r} found in {path.name}")


if __name__ == "__main__":
    unittest.main()
