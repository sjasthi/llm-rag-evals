
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

    def test_vector_chart_uses_page_render_and_provider_metadata(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_path = Path(temporary_directory) / "vector_chart_test.pdf"

            document = pymupdf.open()
            page = document.new_page(width=612, height=792)

            page.insert_text((70, 70), "Fictional Graduate Program Enrollment")

            for index, count in enumerate((40, 60, 80)):
                y = 160 + index * 110
                page.draw_rect(
                    pymupdf.Rect(70, y + 15, 70 + count * 4, y + 50),
                    color=(0.1, 0.3, 0.6),
                    fill=(0.4, 0.6, 0.9),
                )

            page.draw_line((70, 140), (70, 490))
            page.draw_line((70, 490), (500, 490))

            document.save(pdf_path)
            document.close()

            settings = SimpleNamespace(
                vlm_provider="ollama",
                vlm_model="qwen2.5vl:7b",
            )

            expected_analysis = VisualAnalysis(
                content_type="chart",
                content=(
                    "Data Science: 40\n"
                    "Cybersecurity: 60\n"
                    "Computer Science: 80"
                ),
                model="qwen2.5vl:7b",
            )

            with patch(
                "pdf_processor.analyze_visual",
                return_value=expected_analysis,
            ) as mock_analyze:
                elements = process_pdf(pdf_path, settings)

            chart_elements = [
                element
                for element in elements
                if element.content_type == "chart"
            ]

            self.assertEqual(len(chart_elements), 1)
            self.assertEqual(chart_elements[0].page_number, 1)
            self.assertEqual(
                chart_elements[0].extraction_method,
                "ollama_vision_page_render",
            )
            self.assertEqual(
                chart_elements[0].extraction_model,
                "qwen2.5vl:7b",
            )
            self.assertIn("Data Science: 40", chart_elements[0].content)
            self.assertIn("Cybersecurity: 60", chart_elements[0].content)
            self.assertIn("Computer Science: 80", chart_elements[0].content)

            mock_analyze.assert_called_once()

if __name__ == "__main__":
    unittest.main()
