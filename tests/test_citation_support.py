
"""Tests for local citation-to-evidence mapping."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag"))

from citation_support import extract_answer_statements, extract_cited_statements


class CitationSupportMappingTests(unittest.TestCase):

    def test_maps_citation_to_matching_evidence(self):
        statements = extract_cited_statements(
            "Registration takes two days [2].",
            {
                1: "Unrelated admissions information.",
                2: "Registration processing takes two days.",
            },
        )

        self.assertEqual(len(statements), 1)
        self.assertEqual(statements[0].citation_ids, [2])
        self.assertEqual(
            statements[0].evidence,
            {2: "Registration processing takes two days."},
        )

    def test_citation_after_sentence_punctuation(self):
        statements = extract_answer_statements(
            "Registration begins March 23, 2026. [1]",
            {1: "Registration begins March 23, 2026."},
        )

        self.assertEqual(len(statements), 1)
        self.assertEqual(statements[0].citation_ids, [1])
        self.assertTrue(statements[0].has_valid_citation)

    def test_multiple_citations_after_punctuation(self):
        statements = extract_answer_statements(
            "Registration is available online. [1][2]",
            {1: "Online registration.", 2: "Use eServices."},
        )

        self.assertEqual(len(statements), 1)
        self.assertEqual(statements[0].citation_ids, [1, 2])

    def test_citations_stay_with_correct_sentences(self):
        statements = extract_answer_statements(
            "Registration begins March 23. [1] Advising begins April 1. [2]",
            {1: "Registration date.", 2: "Advising date."},
        )

        self.assertEqual(len(statements), 2)
        self.assertEqual(statements[0].citation_ids, [1])
        self.assertEqual(statements[1].citation_ids, [2])

    def test_multiple_citations(self):
        statements = extract_cited_statements(
            "Students can register online [1][3].",
            {
                1: "Online registration is available.",
                3: "Students may use eServices.",
            },
        )

        self.assertEqual(statements[0].citation_ids, [1, 3])
        self.assertEqual(len(statements[0].evidence), 2)

    def test_invalid_citation_is_not_silently_matched(self):
        statements = extract_cited_statements(
            "Registration takes five days [9].",
            {1: "Registration takes two days."},
        )

        self.assertEqual(statements[0].evidence, {})
        self.assertEqual(statements[0].missing_citation_ids, [9])

    def test_duplicate_citations_are_deduplicated(self):
        statements = extract_cited_statements(
            "Registration is online [1][1].",
            {1: "Online registration is available."},
        )

        self.assertEqual(statements[0].citation_ids, [1])

    def test_uncited_answer_returns_no_cited_statements(self):
        statements = extract_cited_statements(
            "Registration is available online.",
            {1: "Online registration is available."},
        )

        self.assertEqual(statements, [])

    def test_multiple_sentences_are_mapped_separately(self):
        statements = extract_cited_statements(
            "Registration takes two days [1]. Advising is available [2].",
            {
                1: "Registration takes two days.",
                2: "Advising is available.",
            },
        )

        self.assertEqual(len(statements), 2)
        self.assertEqual(statements[0].citation_ids, [1])
        self.assertEqual(statements[1].citation_ids, [2])


if __name__ == "__main__":
    unittest.main()
