
"""Unit tests for deterministic content-aware reranking."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag"))

from content_reranker import (
    detect_content_intent,
    rerank_results,
)
from query import SearchResult


class ContentRerankerTests(unittest.TestCase):

    def make_result(
        self,
        rank: int,
        content_type: str,
        text: str,
    ) -> SearchResult:
        return SearchResult(
            rank=rank,
            source_path="test_document.pdf",
            category="Testing",
            chunk_index=rank - 1,
            text=text,
            distance=None,
            keyword_score=None,
            content_type=content_type,
            chunk_id=rank,
            retrieval_score=1.0 / rank,
        )

    def test_detects_table_intent(self):
        question = (
            "What are the intake quantities and assigned "
            "leads for the device categories?"
        )
        self.assertIn("table", detect_content_intent(question))

    def test_detects_diagram_intent(self):
        question = "What are the steps in the collection route diagram?"
        self.assertIn("diagram", detect_content_intent(question))

    def test_preserves_original_order_without_matching_intent(self):
        question = "When does registration begin?"

        candidates = [
            self.make_result(1, "text", "Registration begins in March."),
            self.make_result(2, "table", "Tuition payment details."),
            self.make_result(3, "diagram", "Application process."),
        ]

        results = rerank_results(question, candidates, top_k=3)

        self.assertEqual(
            [result.chunk_id for result in results],
            [1, 2, 3],
        )

    def test_promotes_relevant_table(self):
        question = (
            "According to the Community Device Repair Lab "
            "intake table (FIX-681), what are the intake "
            "quantities and assigned leads for the device "
            "categories listed?"
        )

        candidates = [
            self.make_result(
                1,
                "text",
                "Community Device Repair Lab FIX-681 accepts "
                "small electronics for intake.",
            ),
            self.make_result(
                2,
                "text",
                "Repair Lab collection information.",
            ),
            self.make_result(
                3,
                "diagram",
                "Device intake route diagram.",
            ),
            self.make_result(
                4,
                "table",
                "Device category, daily intake limit, "
                "lead technician. Laptop: 9 devices, "
                "Samira Cole. Tablet: 6 devices, Noah Reed. "
                "Headphones: 12 devices, Lena Park.",
            ),
        ]

        results = rerank_results(question, candidates, top_k=3)

        self.assertIn(
            4,
            [result.chunk_id for result in results],
            "The relevant intake table should reach the top 3.",
        )

    def test_preserves_provenance_and_records_reranking(self):
        candidates = [
            self.make_result(
                1,
                "table",
                "Laptop: 9 devices. Lead technician: Samira Cole.",
            )
        ]

        results = rerank_results(
            "What is the laptop intake quantity?",
            candidates,
            top_k=1,
        )

        result = results[0]

        self.assertEqual(result.chunk_id, 1)
        self.assertEqual(result.content_type, "table")
        self.assertEqual(result.rank, 1)
        self.assertIn(
            "content_reranking",
            result.retrieval_metadata,
        )
        self.assertTrue(
            result.retrieval_metadata["content_reranking"]["enabled"]
        )

    def test_rejects_invalid_top_k(self):
        with self.assertRaises(ValueError):
            rerank_results("test", [], top_k=0)


if __name__ == "__main__":
    unittest.main()
