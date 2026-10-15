
"""Unit tests for structured Markdown document extraction."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Match the existing project's direct module imports.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag"))

from markdown_processor import process_markdown


class MarkdownProcessorTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "test_document.md"

    def write_markdown(self, content: str) -> None:
        self.path.write_text(content, encoding="utf-8")

    def test_extracts_formatted_text_and_headings(self):
        self.write_markdown(
            "# Admissions\n\n"
            "Applicants must submit **official transcripts**.\n\n"
            "## Requirements\n\n"
            "- Completed application\n"
            "- Academic transcripts\n"
        )

        elements = process_markdown(self.path)

        self.assertEqual(len(elements), 2)
        self.assertEqual([e.content_type for e in elements], ["text", "text"])
        self.assertIn("**official transcripts**", elements[0].content)
        self.assertIn("- Completed application", elements[1].content)
        self.assertEqual([e.element_index for e in elements], [1, 2])
        self.assertTrue(all(e.page_number is None for e in elements))
        self.assertTrue(
            all(e.extraction_method == "markdown_parser" for e in elements)
        )

    def test_extracts_table_as_separate_element(self):
        self.write_markdown(
            "# Programs\n\n"
            "| Program | Credits |\n"
            "|---|---|\n"
            "| Computer Science | 120 |\n"
            "| Mathematics | 120 |\n"
        )

        elements = process_markdown(self.path)

        self.assertEqual(len(elements), 2)
        self.assertEqual(elements[0].content_type, "text")
        self.assertEqual(elements[1].content_type, "table")
        self.assertIn("Computer Science | 120", elements[1].content)

    def test_preserves_document_order(self):
        self.write_markdown(
            "# Overview\n\n"
            "Introduction text.\n\n"
            "| Item | Value |\n"
            "|---|---|\n"
            "| A | 10 |\n\n"
            "## Conclusion\n\n"
            "Final remarks.\n"
        )

        elements = process_markdown(self.path)

        self.assertEqual(
            [e.content_type for e in elements],
            ["text", "table", "text"],
        )
        self.assertEqual([e.element_index for e in elements], [1, 2, 3])
        self.assertIn("Conclusion", elements[2].content)

    def test_does_not_interpret_code_fence_as_table(self):
        self.write_markdown(
            "# Code Example\n\n"
            "```markdown\n"
            "| Name | Score |\n"
            "|---|---|\n"
            "| Test | 99 |\n"
            "```\n"
        )

        elements = process_markdown(self.path)

        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].content_type, "text")
        self.assertIn("```markdown", elements[0].content)
        self.assertIn("| Test | 99 |", elements[0].content)

    def test_supports_tilde_code_fences(self):
        self.write_markdown(
            "# Example\n\n"
            "~~~python\n"
            "# Not a Markdown heading\n"
            "print('hello')\n"
            "~~~\n"
        )

        elements = process_markdown(self.path)

        self.assertEqual(len(elements), 1)
        self.assertIn("# Not a Markdown heading", elements[0].content)

    def test_rejects_empty_markdown(self):
        self.write_markdown(" \n \n")

        with self.assertRaisesRegex(ValueError, "no extractable content"):
            process_markdown(self.path)

    def test_rejects_binary_content(self):
        self.path.write_bytes(b"Hello\x00World")

        with self.assertRaisesRegex(ValueError, "binary data"):
            process_markdown(self.path)

    def test_rejects_invalid_utf8(self):
        self.path.write_bytes(b"\xff\xfe\xfa")

        with self.assertRaisesRegex(ValueError, "UTF-8"):
            process_markdown(self.path)

    def test_rejects_missing_file(self):
        with self.assertRaisesRegex(ValueError, "does not exist"):
            process_markdown(self.path)

    def test_preserves_utf8_bom_content(self):
        self.path.write_bytes(
            b"\xef\xbb\xbf# Admissions\n\nRequirements."
        )

        elements = process_markdown(self.path)

        self.assertEqual(len(elements), 1)
        self.assertTrue(elements[0].content.startswith("# Admissions"))


if __name__ == "__main__":
    unittest.main()
