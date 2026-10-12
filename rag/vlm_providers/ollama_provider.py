
"""Ollama implementation of the shared VLM provider interface."""

from __future__ import annotations

import base64
import json
from urllib import error, request


class OllamaVLMProvider:
    """Analyze document visuals using a local Ollama server."""

    def __init__(
        self,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
    ):
        if not model:
            raise ValueError("Ollama model is not configured.")

        self.model = model
        self.base_url = base_url.rstrip("/")

    def analyze(
        self,
        image_bytes: bytes,
        image_format: str,
        system_instruction: str,
        user_instruction: str,
    ) -> str:
        """Return Ollama's raw visual analysis."""

        if not image_bytes:
            raise ValueError("Image data cannot be empty.")

        normalized_format = image_format.lower().removeprefix(".")
        if normalized_format == "jpg":
            normalized_format = "jpeg"

        if normalized_format not in {"png", "jpeg", "webp"}:
            raise ValueError(
                f"Unsupported image format for Ollama: {image_format}"
            )

        encoded_image = base64.b64encode(image_bytes).decode("ascii")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_instruction,
                },
                {
                    "role": "user",
                    "content": user_instruction,
                    "images": [encoded_image],
                },
            ],
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": 1024,
            },
        }

        http_request = request.Request(
            url=f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=180) as response:
                result = json.load(response)

        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Ollama API returned HTTP {exc.code}: {details}"
            ) from exc

        except (error.URLError, TimeoutError) as exc:
            raise RuntimeError(
                f"Unable to communicate with Ollama at {self.base_url}: {exc}"
            ) from exc

        content = (
            result.get("message", {}).get("content", "") or ""
        ).strip()

        if not content:
            raise RuntimeError("Ollama returned an empty visual analysis.")

        return content
