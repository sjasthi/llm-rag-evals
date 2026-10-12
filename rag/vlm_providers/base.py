
"""Shared interface for visual language model providers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

@runtime_checkable
class VLMProvider(Protocol):
    """Contract implemented by Gemini, Ollama, and future VLM providers."""

    def analyze(
        self,
        image_bytes: bytes,
        image_format: str,
        system_instruction: str,
        user_instruction: str,
    ) -> str:
        """Return the model's raw textual analysis of an image."""
        ...
