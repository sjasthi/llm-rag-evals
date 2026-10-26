
import unittest

from rag.citation_validator import (
    REFUSAL_MESSAGE,
    validate_citations,
)


class TestCitationValidator(unittest.TestCase):

    def setUp(self):
        self.sources = [
            {"rank": 1, "original_filename": "TC09_multimodal.pptx"},
            {"rank": 2, "original_filename": "test_case_9_multimodal.pptx"},
            {"rank": 3, "original_filename": "test_case_10_multimodal.docx"},
        ]

    def test_valid_single_citation(self):
        result = validate_citations(
            "Registration Review takes 2 business days [1].",
            self.sources,
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.citation_validity_score, 1.0)

    def test_valid_multiple_citations(self):
        result = validate_citations(
            "Both sources support this answer [1][2].",
            self.sources,
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.valid_citations, [1, 2])

    def test_invalid_citation(self):
        result = validate_citations(
            "Registration Review takes 2 business days [4].",
            self.sources,
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.invalid_citations, [4])
        self.assertEqual(result.citation_validity_score, 0.0)

    def test_mixed_valid_and_invalid(self):
        result = validate_citations(
            "One fact [1]. Another fact [4].",
            self.sources,
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.citation_validity_score, 0.5)

    def test_missing_citations(self):
        result = validate_citations(
            "Registration Review takes 2 business days.",
            self.sources,
        )
        self.assertFalse(result.passed)
        self.assertFalse(result.citation_presence_passed)
        self.assertIsNone(result.citation_validity_score)

    def test_duplicate_citations(self):
        result = validate_citations(
            "First fact [1]. Second fact [1].",
            self.sources,
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.citations_found, [1])

    def test_refusal_without_citations(self):
        result = validate_citations(
            REFUSAL_MESSAGE,
            self.sources,
        )
        self.assertTrue(result.passed)
        self.assertTrue(result.is_refusal)
        self.assertFalse(result.has_citations)

    def test_empty_sources(self):
        result = validate_citations(
            "A factual answer [1].",
            [],
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.invalid_citations, [1])


if __name__ == "__main__":
    unittest.main()
