
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

    def test_regular_table_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_path = Path(temporary_directory) / "regular_table.pdf"

            document = pymupdf.open()
            page = document.new_page()

            x_positions = [70, 240, 400, 540]
            y_positions = [120, 160, 200, 240]

            for x in x_positions:
                page.draw_line((x, 120), (x, 240))

            for y in y_positions:
                page.draw_line((70, y), (540, y))

            rows = [
                ("Program", "GPA", "Credits"),
                ("Data Science", "3.25", "32"),
                ("Cybersecurity", "3.00", "34"),
            ]

            for row_index, row in enumerate(rows):
                for column_index, value in enumerate(row):
                    page.insert_text(
                        (
                            x_positions[column_index] + 10,
                            y_positions[row_index] + 25,
                        ),
                        value,
                        fontsize=10,
                    )

            document.save(pdf_path)
            document.close()

            elements = process_pdf(pdf_path)

            tables = [
                element
                for element in elements
                if element.content_type == "table"
            ]

            self.assertEqual(len(tables), 1)
            self.assertIn("Data Science", tables[0].content)
            self.assertIn("Cybersecurity", tables[0].content)
            self.assertIn("3.25", tables[0].content)
            self.assertEqual(
                tables[0].extraction_method,
                "pymupdf_table",
            )

    def test_multiline_table_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_path = Path(temporary_directory) / "multiline_table.pdf"

            document = pymupdf.open()
            page = document.new_page()

            x_positions = [70, 280, 540]
            y_positions = [120, 165, 310]

            for x in x_positions:
                page.draw_line((x, 120), (x, 310))

            for y in y_positions:
                page.draw_line((70, y), (540, y))

            page.insert_text((85, 145), "Program", fontsize=11)
            page.insert_text((295, 145), "Requirements", fontsize=11)
            page.insert_text((85, 190), "Data Science", fontsize=11)

            requirements = [
                "Complete an online application",
                "Submit official transcripts",
                "Provide a statement of purpose",
                "Submit two recommendation letters",
                "Meet the minimum GPA requirement",
            ]

            for index, requirement in enumerate(requirements):
                page.insert_text(
                    (295, 190 + index * 20),
                    requirement,
                    fontsize=9,
                )

            document.save(pdf_path)
            document.close()

            elements = process_pdf(pdf_path)

            tables = [
                element
                for element in elements
                if element.content_type == "table"
            ]

            self.assertEqual(len(tables), 1)

            for requirement in requirements:
                self.assertIn(requirement, tables[0].content)

            self.assertIn("Data Science", tables[0].content)

    def test_flowchart_false_positive_table_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_path = Path(temporary_directory) / "flowchart.pdf"

            document = pymupdf.open()
            page = document.new_page(width=612, height=792)

            page.insert_text(
                (70, 65),
                "Fictional Graduate Admissions Workflow",
                fontsize=16,
            )

            boxes = [
                (pymupdf.Rect(170, 100, 440, 155), "Submit Application"),
                (pymupdf.Rect(170, 200, 440, 255), "Review Documents"),
                (pymupdf.Rect(170, 300, 440, 355), "Admission Decision"),
                (pymupdf.Rect(65, 535, 275, 590), "Send Acceptance"),
                (pymupdf.Rect(335, 535, 545, 590), "Send Rejection"),
            ]

            for rect, label in boxes:
                page.draw_rect(rect, color=(0, 0, 0))
                page.insert_text(
                    (rect.x0 + 12, rect.y0 + 30),
                    label,
                    fontsize=11,
                )

            page.draw_line((305, 155), (305, 200))
            page.draw_line((305, 255), (305, 300))
            page.draw_line((305, 355), (305, 450))
            page.draw_line((170, 450), (440, 450))
            page.draw_line((170, 450), (170, 535))
            page.draw_line((440, 450), (440, 535))

            page.insert_text((105, 475), "Approved", fontsize=10)
            page.insert_text((380, 475), "Denied", fontsize=10)

            document.save(pdf_path)
            document.close()

            settings = SimpleNamespace(
                vlm_provider="ollama",
                vlm_model="qwen2.5vl:7b",
            )

            expected_analysis = VisualAnalysis(
                content_type="diagram",
                content=(
                    "Submit Application -> Review Documents -> "
                    "Admission Decision; "
                    "Approved -> Send Acceptance; "
                    "Denied -> Send Rejection"
                ),
                model="qwen2.5vl:7b",
            )

            with patch(
                "pdf_processor.analyze_visual",
                return_value=expected_analysis,
            ) as mock_analyze:
                elements = process_pdf(pdf_path, settings)

            element_types = [
                element.content_type
                for element in elements
            ]

            self.assertIn("text", element_types)
            self.assertIn("diagram", element_types)
            self.assertNotIn("table", element_types)

            text_element = next(
                element
                for element in elements
                if element.content_type == "text"
            )

            self.assertIn("Submit Application", text_element.content)
            self.assertIn("Admission Decision", text_element.content)
            self.assertIn("Send Acceptance", text_element.content)
            self.assertIn("Send Rejection", text_element.content)

            diagram_element = next(
                element
                for element in elements
                if element.content_type == "diagram"
            )

            self.assertEqual(
                diagram_element.extraction_method,
                "ollama_vision_page_render",
            )
            self.assertEqual(
                diagram_element.extraction_model,
                "qwen2.5vl:7b",
            )

            mock_analyze.assert_called_once()

if __name__ == "__main__":
    unittest.main()
