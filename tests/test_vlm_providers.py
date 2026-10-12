
"""Tests for configurable visual-language-model providers."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "rag"),
)

from visual_processor import analyze_visual


class VLMProviderTests(unittest.TestCase):

    def make_settings(self, provider):
        return SimpleNamespace(
            vlm_provider=provider,
            vlm_model=(
                "qwen2.5vl:7b"
                if provider == "ollama"
                else "gemini-test-model"
            ),
            llm_api_key="fake-test-key",
            ollama_base_url="http://127.0.0.1:11434",
        )

    @patch("visual_processor.GeminiVLMProvider")
    def test_gemini_provider_selection(self, mock_provider):
        mock_provider.return_value.analyze.return_value = (
            "TYPE: chart\n"
            "Data Science requires a 3.25 GPA."
        )

        result = analyze_visual(
            image_bytes=b"fake-image",
            image_format="png",
            settings=self.make_settings("gemini"),
        )

        mock_provider.assert_called_once_with(
            api_key="fake-test-key",
            model="gemini-test-model",
        )

        self.assertEqual(result.content_type, "chart")
        self.assertEqual(
            result.content,
            "Data Science requires a 3.25 GPA.",
        )
        self.assertEqual(result.model, "gemini-test-model")

    @patch("visual_processor.OllamaVLMProvider")
    def test_ollama_provider_selection(self, mock_provider):
        mock_provider.return_value.analyze.return_value = (
            "TYPE: scanned_page\n"
            "Cybersecurity requires 34 credits."
        )

        result = analyze_visual(
            image_bytes=b"fake-image",
            image_format="png",
            settings=self.make_settings("ollama"),
        )

        mock_provider.assert_called_once_with(
            model="qwen2.5vl:7b",
            base_url="http://127.0.0.1:11434",
        )

        self.assertEqual(result.content_type, "scanned_page")
        self.assertEqual(
            result.content,
            "Cybersecurity requires 34 credits.",
        )
        self.assertEqual(result.model, "qwen2.5vl:7b")

    def test_unsupported_provider_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "Unsupported VLM provider",
        ):
            analyze_visual(
                image_bytes=b"fake-image",
                image_format="png",
                settings=self.make_settings("invalid"),
            )

    def test_empty_image_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "Image data cannot be empty",
        ):
            analyze_visual(
                image_bytes=b"",
                image_format="png",
                settings=self.make_settings("ollama"),
            )

    @patch("visual_processor.OllamaVLMProvider")
    def test_empty_provider_response_is_rejected(self, mock_provider):
        mock_provider.return_value.analyze.return_value = "  "

        with self.assertRaisesRegex(
            RuntimeError,
            "VLM returned an empty visual analysis",
        ):
            analyze_visual(
                image_bytes=b"fake-image",
                image_format="png",
                settings=self.make_settings("ollama"),
            )

    @patch("visual_processor.OllamaVLMProvider")
    def test_unknown_classification_defaults_to_other(self, mock_provider):
        mock_provider.return_value.analyze.return_value = (
            "TYPE: unknown\n"
            "A diagram showing three connected components."
        )

        result = analyze_visual(
            image_bytes=b"fake-image",
            image_format="png",
            settings=self.make_settings("ollama"),
        )

        self.assertEqual(result.content_type, "other")
        self.assertEqual(
            result.content,
            "A diagram showing three connected components.",
        )


if __name__ == "__main__":
    unittest.main()
