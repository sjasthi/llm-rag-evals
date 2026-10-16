
"""Integration tests for Markdown extraction and retrieval preparation."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag"))

from ingest import (
    prepare_multimodal_document,
    prepare_document_chunks,
    prepare_markdown_document,
    read_documents,
    stable_chroma_id,
)


class MarkdownIngestionTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.directory = Path(self.temp_dir.name)
        self.path = self.directory / "admissions_test.md"

        self.path.write_text(
            "# Metro State Admissions\n\n"
            "Applicants must submit **official transcripts**.\n\n"
            "## Program Requirements\n\n"
            "| Program | Minimum GPA |\n"
            "|---|---|\n"
            "| Computer Science | 2.5 |\n"
            "| Mathematics | 2.0 |\n",
            encoding="utf-8",
        )

        self.source_path = "test/admissions_test.md"

    def test_markdown_creates_structured_elements_and_chunks(self):
        prepared = prepare_multimodal_document(
            self.path,
            source_path=self.source_path,
            category="test",
            chunk_size=800,
        )

        self.assertEqual(len(prepared.elements), 3)
        self.assertEqual(
            [element.content_type for element in prepared.elements],
            ["text", "text", "table"],
        )

        self.assertEqual(len(prepared.chunks), 3)
        self.assertEqual(
            [chunk.content_type for chunk in prepared.chunks],
            ["text", "text", "table"],
        )

        self.assertEqual(
            [chunk.element_index for chunk in prepared.chunks],
            [1, 2, 3],
        )

        for chunk in prepared.chunks:
            self.assertEqual(chunk.source_type, "md")
            self.assertEqual(chunk.original_filename, "admissions_test.md")
            self.assertEqual(chunk.extraction_method, "markdown_parser")
            self.assertIsNone(chunk.page_number)
            self.assertIsNone(chunk.extraction_model)
            self.assertEqual(chunk.source_path, self.source_path)

        self.assertIn(
            "**official transcripts**",
            prepared.chunks[0].text,
        )
        self.assertIn(
            "Computer Science | 2.5",
            prepared.chunks[2].text,
        )

    def test_markdown_has_stable_chroma_identifiers(self):
        prepared = prepare_multimodal_document(
            self.path,
            source_path=self.source_path,
            category="test",
            chunk_size=800,
        )

        self.assertEqual(
            [chunk.chroma_id for chunk in prepared.chunks],
            [
                stable_chroma_id(self.source_path, 0),
                stable_chroma_id(self.source_path, 1),
                stable_chroma_id(self.source_path, 2),
            ],
        )

    def test_direct_chunk_preparation_supports_markdown(self):
        chunks = prepare_document_chunks(
            self.path,
            source_path=self.source_path,
            category="test",
            chunk_size=800,
            overlap=100,
        )

        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[2].content_type, "table")
        self.assertEqual(chunks[2].source_type, "md")

    def test_document_discovery_includes_markdown(self):
        documents = read_documents(self.directory)

        self.assertEqual(documents, [self.path])

    def test_mermaid_diagram_becomes_searchable_chunk(self):
        self.path.write_text(
            "# Application Review\n\n"
            "The admissions office reviews student applications.\n\n"
            "```mermaid\n"
            "flowchart TD\n"
            "    A[Submit Application] --> B{Requirements Met?}\n"
            "    B -->|Yes| C[Application Accepted]\n"
            "    B -->|No| D[Application Rejected]\n"
            "```\n",
            encoding="utf-8",
        )

        prepared = prepare_markdown_document(
            self.path,
            source_path="test_document.md",
            category="admissions",
            chunk_size=800,
        )

        diagram_elements = [
            element
            for element in prepared.elements
            if element.content_type == "diagram"
        ]

        diagram_chunks = [
            chunk
            for chunk in prepared.chunks
            if chunk.content_type == "diagram"
        ]

        self.assertEqual(len(diagram_elements), 1)
        self.assertEqual(len(diagram_chunks), 1)

        diagram = diagram_elements[0]
        chunk = diagram_chunks[0]

        self.assertEqual(diagram.extraction_method, "mermaid_source")
        self.assertEqual(chunk.extraction_method, "mermaid_source")
        self.assertEqual(chunk.source_type, "md")
        self.assertIsNone(chunk.extraction_model)
        self.assertIsNone(chunk.page_number)

        self.assertIn("B -->|Yes| C[Application Accepted]", chunk.text)
        self.assertIn("B -->|No| D[Application Rejected]", chunk.text)

if __name__ == "__main__":
    unittest.main()
