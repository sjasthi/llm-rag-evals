"""Regression tests for the V2 multimodal RAG pipeline."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "rag"))

from ingest import prepare_pdf_document
from visual_processor import VisualAnalysis


class V2MultimodalRAGPipelineTests(unittest.TestCase):

    def test_pdf_diagram_becomes_retrievable_chunk(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_path = Path(temporary_directory) / "admissions_diagram.pdf"

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

            diagram_description = (
                "Graduate Admissions Workflow: "
                "Submit Application -> Review Documents -> "
                "Admission Decision. "
                "Approved -> Send Acceptance. "
                "Denied -> Send Rejection."
            )

            analysis = VisualAnalysis(
                content_type="diagram",
                content=diagram_description,
                model="qwen2.5vl:7b",
            )

            with (
                patch(
                    "pdf_processor.analyze_visual",
                    return_value=analysis,
                ) as mock_analyze,
                patch("ingest.load_settings") as mock_settings,
            ):
                mock_settings.return_value.vlm_provider = "ollama"
                mock_settings.return_value.vlm_model = "qwen2.5vl:7b"
                prepared = prepare_pdf_document(
                    pdf_path,
                    source_path="v2_test/admissions_diagram.pdf",
                    category="v2_test",
                    chunk_size=800,
                )

            mock_analyze.assert_called_once()

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

            element = diagram_elements[0]
            chunk = diagram_chunks[0]

            self.assertEqual(chunk.text, diagram_description)
            self.assertEqual(chunk.page_number, 1)
            self.assertEqual(chunk.element_index, element.element_index)
            self.assertEqual(chunk.extraction_method, "ollama_vision_page_render")
            self.assertEqual(chunk.extraction_model, "qwen2.5vl:7b")
            self.assertEqual(chunk.source_type, "pdf")
            self.assertEqual(chunk.category, "v2_test")
            self.assertIn("Denied -> Send Rejection", chunk.text)


    def test_diagram_evidence_reaches_answer_generator(self):
        from answer import answer_question
        from query import SearchResult

        diagram_description = (
            "Graduate Admissions Workflow: "
            "Submit Application -> Review Documents -> "
            "Admission Decision. "
            "Approved -> Send Acceptance. "
            "Denied -> Send Rejection."
        )

        diagram_context = SearchResult(
            rank=1,
            source_path="v2_test/admissions_diagram.pdf",
            category="v2_test",
            chunk_index=1,
            text=diagram_description,
            distance=0.4,
            keyword_score=3,
            document_id=1,
            chunk_id=2,
            element_id=2,
            page_number=1,
            content_type="diagram",
            extraction_method="ollama_vision_page_render",
            extraction_model="qwen2.5vl:7b",
        )

        def fake_generator(prompt, _settings):
            self.assertIn(
                "Denied -> Send Rejection",
                prompt,
            )
            self.assertIn(
                "admissions_diagram.pdf",
                prompt,
            )
            return "A rejection is sent."

        with patch(
            "answer.semantic_search",
            return_value=[diagram_context],
        ) as mock_search:
            result = answer_question(
                "What happens when a graduate application is denied?",
                top_k=2,
                save=False,
                retrieval_method="chroma_vector",
                categories=["v2_test"],
                generator=fake_generator,
            )

        self.assertEqual(result.answer, "A rejection is sent.")
        self.assertEqual(len(result.sources), 1)
        self.assertIsNone(result.response_id)

        source = result.sources[0]
        self.assertEqual(source.content_type, "diagram")
        self.assertEqual(source.page_number, 1)
        self.assertEqual(
            source.extraction_method,
            "ollama_vision_page_render",
        )
        self.assertEqual(
            source.extraction_model,
            "qwen2.5vl:7b",
        )

        mock_search.assert_called_once()


if __name__ == "__main__":
    unittest.main()
