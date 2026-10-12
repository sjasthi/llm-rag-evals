
"""Gemini implementation of the shared VLM provider interface."""

from __future__ import annotations

import time

from google import genai
from google.genai import types


class GeminiVLMProvider:
    """Analyze document visuals using Google's Gemini API."""

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError("Gemini API key is not configured.")

        self.api_key = api_key
        self.model = model

    def analyze(
        self,
        image_bytes: bytes,
        image_format: str,
        system_instruction: str,
        user_instruction: str,
    ) -> str:
        """Return Gemini's raw visual analysis."""

        if not image_bytes:
            raise ValueError("Image data cannot be empty.")

        normalized_format = image_format.lower()
        if normalized_format == "jpg":
            normalized_format = "jpeg"

        mime_type = f"image/{normalized_format}"

        client = genai.Client(api_key=self.api_key)
        max_attempts = 3

        try:
            for attempt in range(1, max_attempts + 1):
                try:
                    response = client.models.generate_content(
                        model=self.model,
                        contents=[
                            types.Part.from_bytes(
                                data=image_bytes,
                                mime_type=mime_type,
                            ),
                            user_instruction,
                        ],
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.0,
                            max_output_tokens=1024,
                        ),
                    )
                    break

                except Exception as error:
                    error_text = str(error).lower()

                    is_temporary_error = (
                        "503" in error_text
                        or "unavailable" in error_text
                        or "high demand" in error_text
                    )

                    if not is_temporary_error or attempt == max_attempts:
                        raise

                    wait_seconds = attempt * 2

                    print(
                        f"Warning: Gemini visual analysis attempt "
                        f"{attempt} failed temporarily. "
                        f"Retrying in {wait_seconds} seconds..."
                    )

                    time.sleep(wait_seconds)

        finally:
            client.close()

        content = (response.text or "").strip()

        if not content:
            raise RuntimeError("Gemini returned an empty visual analysis.")

        return content
