
"""Tests for PDF visual extraction and provider provenance."""

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pymupdf

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "rag"),
)

from pdf_processor import process_pdf
from visual_processor import VisualAnalysis


class PDFVisualIntegrationTests(unittest.TestCase):

    def test_embedded_image_uses_selected_provider_metadata(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_path = Path(temporary_directory) / "image_test.pdf"

            document = pymupdf.open()
            page = document.new_page()

            # Generate a small image entirely in memory.
            image_document = pymupdf.open()
            image_page = image_document.new_page(
                width=200,
                height=100,
            )
            image_page.insert_text(
                (20, 50),
                "Test visual content",
            )
            image_bytes = image_page.get_pixmap().tobytes("png")
            image_document.close()

            page.insert_image(
                pymupdf.Rect(50, 100, 250, 200),
                stream=image_bytes,
            )

            document.save(pdf_path)
            document.close()

            settings = SimpleNamespace(
                vlm_provider="ollama",
                vlm_model="qwen2.5vl:7b",
            )

            expected_analysis = VisualAnalysis(
                content_type="image",
                content="Test visual content",
                model="qwen2.5vl:7b",
            )

            with patch(
                "pdf_processor.analyze_visual",
                return_value=expected_analysis,
            ) as mock_analyze:
                elements = process_pdf(pdf_path, settings)

            visual_elements = [
                element
                for element in elements
                if element.extraction_method == "ollama_vision"
            ]

            self.assertEqual(len(visual_elements), 1)
            self.assertEqual(visual_elements[0].page_number, 1)
            self.assertEqual(visual_elements[0].content_type, "image")
            self.assertEqual(
                visual_elements[0].content,
                "Test visual content",
            )
            self.assertEqual(
                visual_elements[0].extraction_model,
                "qwen2.5vl:7b",
            )
            mock_analyze.assert_called_once()


if __name__ == "__main__":
    unittest.main()
