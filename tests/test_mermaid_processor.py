"""Unit tests for Mermaid flowchart relationship extraction."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag"))

from mermaid_processor import describe_mermaid_flowchart
from chunking import chunk_element
from pdf_processor import DocumentElement


class MermaidProcessorTests(unittest.TestCase):

    def test_describes_labeled_decision_branches(self):
        source = (
            "```mermaid\n"
            "flowchart TD\n"
            "A[Student Submits Application] --> B{All Documents Received?}\n"
            "B -->|No| C[Request Missing Documents]\n"
            "B -->|Yes| D[Faculty Review]\n"
            "```\n"
        )

        description = describe_mermaid_flowchart(source)

        self.assertIn(
            '"Student Submits Application" leads to '
            '"All Documents Received?".',
            description,
        )
        self.assertIn(
            'From "All Documents Received?", the "No" branch '
            'leads to "Request Missing Documents".',
            description,
        )
        self.assertIn(
            'From "All Documents Received?", the "Yes" branch '
            'leads to "Faculty Review".',
            description,
        )

    def test_describes_missing_document_loop(self):
        source = (
            "flowchart TD\n"
            "B{All Documents Received?} -->|No| C[Request Missing Documents]\n"
            "C --> D[Wait for Student Response]\n"
            "D --> B\n"
        )

        description = describe_mermaid_flowchart(source)

        self.assertIn(
            '"Request Missing Documents" leads to '
            '"Wait for Student Response".',
            description,
        )
        self.assertIn(
            '"Wait for Student Response" leads to '
            '"All Documents Received?".',
            description,
        )

    def test_preserves_original_source_in_retrieval_chunk(self):
        source = (
            "```mermaid\n"
            "flowchart LR\n"
            "A[Start] --> B[Finish]\n"
            "```\n"
        )

        element = DocumentElement(
            content_type="diagram",
            content=source,
            page_number=None,
            element_index=1,
            extraction_method="mermaid_source",
        )

        chunks = chunk_element(element)

        self.assertEqual(len(chunks), 1)
        self.assertIn(
            '"Start" leads to "Finish".',
            chunks[0].content,
        )
        self.assertIn("Original Mermaid source:", chunks[0].content)
        self.assertIn("A[Start] --> B[Finish]", chunks[0].content)
        self.assertEqual(chunks[0].extraction_method, "mermaid_source")

    def test_does_not_modify_pdf_diagram_chunks(self):
        element = DocumentElement(
            content_type="diagram",
            content="A visual diagram describing a manufacturing workflow.",
            page_number=2,
            element_index=1,
            extraction_method="ollama_vision_page_render",
            extraction_model="qwen2.5vl:7b",
        )

        chunks = chunk_element(element)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].content, element.content)
        self.assertEqual(
            chunks[0].extraction_method,
            "ollama_vision_page_render",
        )

    def test_unsupported_diagram_returns_no_description(self):
        source = (
            "```mermaid\n"
            "sequenceDiagram\n"
            "Alice->>Bob: Hello\n"
            "```\n"
        )

        self.assertEqual(describe_mermaid_flowchart(source), "")

    def test_describes_connected_workflow_paths(self):
        source = """
```mermaid
flowchart TD
    A[Student Submits Application] --> B{All Documents Received?}
    B -->|No| C[Request Missing Documents]
    C --> D[Wait for Student Response]
    D --> B
```
"""

        description = describe_mermaid_flowchart(source)

        self.assertIn(
            'The workflow proceeds from "Request Missing Documents" '
            'to "Wait for Student Response", '
            'then to "All Documents Received?".',
            description,
        )

        self.assertIn(
            'When the "No" branch is taken at '
            '"All Documents Received?", the workflow proceeds to '
            '"Request Missing Documents", '
            'then to "Wait for Student Response".',
            description,
        )

if __name__ == "__main__":
    unittest.main()