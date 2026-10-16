
"""Unit tests for Reciprocal Rank Fusion retrieval."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag"))

from query import SearchResult, reciprocal_rank_fusion


def make_result(
    chunk_id: int,
    rank: int,
    content_type: str = "text",
) -> SearchResult:
    return SearchResult(
        rank=rank,
        source_path="storage/uploads/test.md",
        category="input_test",
        chunk_index=chunk_id,
        text=f"Test chunk {chunk_id}",
        distance=0.5,
        keyword_score=3.0,
        document_id=10,
        chunk_id=chunk_id,
        element_id=chunk_id + 100,
        content_type=content_type,
        extraction_method="mermaid_source" if content_type == "diagram" else "markdown_parser",
    )


class ReciprocalRankFusionTests(unittest.TestCase):

    def test_combines_rankings_from_two_methods(self):
        chroma = [make_result(1, 1), make_result(2, 2)]
        mysql = [make_result(2, 1), make_result(1, 2)]

        results = reciprocal_rank_fusion([chroma, mysql], top_k=2)

        self.assertEqual(len(results), 2)
        self.assertEqual({r.chunk_id for r in results}, {1, 2})
        self.assertAlmostEqual(
            results[0].retrieval_score,
            1 / 61 + 1 / 62,
        )

    def test_chunk_found_by_only_one_method_is_included(self):
        chroma = [make_result(1, 1)]
        mysql = [make_result(2, 1)]

        results = reciprocal_rank_fusion([chroma, mysql], top_k=2)

        self.assertEqual({r.chunk_id for r in results}, {1, 2})

    def test_duplicate_chunk_is_returned_once(self):
        chroma = [make_result(1, 1), make_result(1, 2)]
        mysql = [make_result(1, 1)]

        results = reciprocal_rank_fusion([chroma, mysql], top_k=5)

        self.assertEqual(len(results), 1)
        self.assertAlmostEqual(
            results[0].retrieval_score,
            2 / 61,
        )

    def test_preserves_mermaid_provenance(self):
        diagram = make_result(3, 1, content_type="diagram")

        results = reciprocal_rank_fusion([[diagram], []], top_k=1)

        self.assertEqual(results[0].content_type, "diagram")
        self.assertEqual(results[0].extraction_method, "mermaid_source")
        self.assertEqual(results[0].element_id, 103)
        self.assertEqual(results[0].retrieval_metadata["version"], "rrf-v1")

    def test_rejects_invalid_arguments(self):
        with self.assertRaises(ValueError):
            reciprocal_rank_fusion([], top_k=0)

        with self.assertRaises(ValueError):
            reciprocal_rank_fusion([], top_k=1, k=0)


if __name__ == "__main__":
    unittest.main()
