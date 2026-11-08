"""Provider routing regression tests without external API calls."""

import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "rag"),
)

import llm
from settings import load_settings


class ProviderRoutingTests(unittest.TestCase):

    def setUp(self):
        self.settings = load_settings()

    def test_gemini_routes_to_gemini(self):
        settings = replace(
            self.settings,
            llm_provider="gemini",
            llm_chat_model="gemini-test-model",
        )
        expected = llm.GenerationExecution(
            answer="Gemini response",
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
        )

        with patch.object(
            llm, "generate_with_gemini", return_value=expected
        ) as gemini, patch.object(
            llm, "generate_with_ollama"
        ) as ollama:
            actual = llm.generate_grounded_answer(
                "Test prompt", settings
            )

        self.assertEqual(actual, expected)
        gemini.assert_called_once_with("Test prompt", settings)
        ollama.assert_not_called()

    def test_ollama_routes_to_ollama(self):
        settings = replace(
            self.settings,
            llm_provider="ollama",
            llm_chat_model="qwen2.5vl:7b",
        )
        expected = llm.GenerationExecution(
            answer="Ollama response",
            input_tokens=12,
            output_tokens=6,
            total_tokens=18,
        )

        with patch.object(
            llm, "generate_with_ollama", return_value=expected
        ) as ollama, patch.object(
            llm, "generate_with_gemini"
        ) as gemini:
            actual = llm.generate_grounded_answer(
                "Test prompt", settings
            )

        self.assertEqual(actual, expected)
        ollama.assert_called_once_with("Test prompt", settings)
        gemini.assert_not_called()

    def test_unsupported_provider_is_rejected(self):
        settings = replace(
            self.settings,
            llm_provider="unsupported",
        )

        with self.assertRaisesRegex(
            ValueError, "Unsupported LLM_PROVIDER"
        ):
            llm.generate_grounded_answer(
                "Test prompt", settings
            )


if __name__ == "__main__":
    unittest.main()
