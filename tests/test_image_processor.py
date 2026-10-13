
"""Unit tests for standalone PNG/JPEG visual extraction."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pymupdf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "rag"))

from image_processor import process_image
from visual_processor import VisualAnalysis

from ingest import prepare_image_document, prepare_multimodal_document, read_documents


class ImageProcessorTests(unittest.TestCase):
    """Verify standalone image validation and extraction metadata."""

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.directory = Path(self.temporary_directory.name)

        self.settings = Mock()
        self.settings.vlm_provider = "ollama"
        self.settings.vlm_model = "qwen2.5vl:7b"

    def create_image(self, filename: str) -> Path:
        """Generate a valid image without requiring external test fixtures."""
        path = self.directory / filename

        pixmap = pymupdf.Pixmap(pymupdf.csRGB, (0, 0, 32, 32), False)
        try:
            pixmap.save(str(path))
        finally:
            del pixmap

        return path

    def test_png_produces_searchable_element(self):
        path = self.create_image("admissions.png")

        analysis = VisualAnalysis(
            content_type="diagram",
            content="Application denied -> Send Rejection.",
            model="qwen2.5vl:7b",
        )

        with patch(
            "image_processor.analyze_visual",
            return_value=analysis,
        ) as mock_analyze:
            elements = process_image(path, self.settings)

        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].content_type, "diagram")
        self.assertEqual(elements[0].content, analysis.content)
        self.assertEqual(elements[0].page_number, 1)
        self.assertEqual(elements[0].element_index, 1)
        self.assertEqual(elements[0].extraction_method, "ollama_vision")
        self.assertEqual(elements[0].extraction_model, "qwen2.5vl:7b")

        args, _ = mock_analyze.call_args
        self.assertEqual(args[1], "png")
        self.assertEqual(args[2], self.settings)
        self.assertTrue(args[0])

    def test_jpeg_uses_correct_image_format(self):
        path = self.create_image("admissions.jpg")

        analysis = VisualAnalysis(
            content_type="image",
            content="An informational admissions screenshot.",
            model="qwen2.5vl:7b",
        )

        with patch(
            "image_processor.analyze_visual",
            return_value=analysis,
        ) as mock_analyze:
            elements = process_image(path, self.settings)

        self.assertEqual(len(elements), 1)
        self.assertEqual(mock_analyze.call_args.args[1], "jpeg")

    def test_empty_image_is_rejected(self):
        path = self.directory / "empty.png"
        path.write_bytes(b"")

        with patch("image_processor.analyze_visual") as mock_analyze:
            with self.assertRaisesRegex(ValueError, "empty"):
                process_image(path, self.settings)

        mock_analyze.assert_not_called()

    def test_invalid_image_data_is_rejected(self):
        path = self.directory / "invalid.png"
        path.write_bytes(b"Not a valid image")

        with patch("image_processor.analyze_visual") as mock_analyze:
            with self.assertRaisesRegex(ValueError, "invalid"):
                process_image(path, self.settings)

        mock_analyze.assert_not_called()

    def test_unsupported_extension_is_rejected(self):
        path = self.directory / "image.gif"
        path.write_bytes(b"some data")

        with self.assertRaisesRegex(ValueError, "Unsupported"):
            process_image(path, self.settings)

    def test_missing_file_is_rejected(self):
        path = self.directory / "missing.png"

        with self.assertRaisesRegex(ValueError, "does not exist"):
            process_image(path, self.settings)

    def test_empty_visual_analysis_is_rejected(self):
        path = self.create_image("empty_analysis.png")

        analysis = VisualAnalysis(
            content_type="image",
            content="   ",
            model="qwen2.5vl:7b",
        )

        with patch(
            "image_processor.analyze_visual",
            return_value=analysis,
        ):
            with self.assertRaisesRegex(ValueError, "no searchable content"):
                process_image(path, self.settings)

    def test_image_document_produces_retrieval_chunk(self):
        """Image evidence should retain source and VLM provenance."""
        path = self.create_image("admissions.png")

        analysis = VisualAnalysis(
            content_type="diagram",
            content="Application denied -> Send Rejection.",
            model="qwen2.5vl:7b",
        )

        with (
            patch(
                "image_processor.analyze_visual",
                return_value=analysis,
            ),
            patch("ingest.load_settings", return_value=self.settings),
        ):
            prepared = prepare_image_document(
                path,
                source_path="v2_test/admissions.png",
                category="v2_test",
                chunk_size=800,
            )

        self.assertEqual(len(prepared.elements), 1)
        self.assertEqual(len(prepared.chunks), 1)

        element = prepared.elements[0]
        chunk = prepared.chunks[0]

        self.assertEqual(element.content_type, "diagram")
        self.assertEqual(chunk.text, analysis.content)
        self.assertEqual(chunk.source_path, "v2_test/admissions.png")
        self.assertEqual(chunk.category, "v2_test")
        self.assertEqual(chunk.source_type, "png")
        self.assertEqual(chunk.original_filename, "admissions.png")
        self.assertEqual(chunk.content_type, "diagram")
        self.assertEqual(chunk.page_number, 1)
        self.assertEqual(chunk.element_index, 1)
        self.assertEqual(chunk.element_chunk_index, 1)
        self.assertEqual(chunk.extraction_method, "ollama_vision")
        self.assertEqual(chunk.extraction_model, "qwen2.5vl:7b")
        self.assertTrue(chunk.source_hash)
        self.assertTrue(chunk.chroma_id)


    def test_multimodal_dispatch_supports_all_image_extensions(self):
        """PNG, JPG, and JPEG should use the image preparation pipeline."""
        for extension in (".png", ".jpg", ".jpeg"):
            with self.subTest(extension=extension):
                path = self.directory / f"test{extension}"

                expected = Mock()

                with patch(
                    "ingest.prepare_image_document",
                    return_value=expected,
                ) as mock_prepare:
                    result = prepare_multimodal_document(
                        path,
                        source_path=f"test/test{extension}",
                        category="test",
                        chunk_size=800,
                    )

                self.assertIs(result, expected)
                mock_prepare.assert_called_once_with(
                    path,
                    source_path=f"test/test{extension}",
                    category="test",
                    chunk_size=800,
                )

    def test_multimodal_dispatch_rejects_unsupported_format(self):
        """Unsupported formats should not enter a multimodal processor."""
        path = self.directory / "test.gif"

        with self.assertRaisesRegex(
            ValueError,
            "Unsupported multimodal document type",
        ):
            prepare_multimodal_document(
                path,
                source_path="test/test.gif",
                category="test",
                chunk_size=800,
            )

    def test_document_discovery_includes_supported_images(self):
        """Directory ingestion should discover PNG, JPG, and JPEG files."""
        filenames = (
            "diagram.png",
            "chart.jpg",
            "screenshot.jpeg",
            "notes.txt",
            "unsupported.gif",
        )

        for filename in filenames:
            (self.directory / filename).write_bytes(b"test")

        discovered = read_documents(self.directory)
        discovered_names = {path.name for path in discovered}

        self.assertEqual(
            discovered_names,
            {
                "diagram.png",
                "chart.jpg",
                "screenshot.jpeg",
                "notes.txt",
            },
        )

if __name__ == "__main__":
    unittest.main()
