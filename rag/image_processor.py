
"""Extract searchable visual evidence from standalone PNG and JPEG files."""

from __future__ import annotations

from pathlib import Path

import pymupdf

from pdf_processor import DocumentElement
from settings import Settings
from visual_processor import analyze_visual


SUPPORTED_IMAGE_FORMATS = {
    ".png": "png",
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
}


def process_image(
    path: Path,
    settings: Settings,
) -> list[DocumentElement]:
    """Validate an image and convert it into one searchable document element."""
    path = path.resolve()

    if not path.is_file():
        raise ValueError(f"Image file does not exist: {path}")

    image_format = SUPPORTED_IMAGE_FORMATS.get(path.suffix.lower())

    if image_format is None:
        raise ValueError("Unsupported image format. Use PNG or JPEG.")

    image_bytes = path.read_bytes()

    if not image_bytes:
        raise ValueError("Image file is empty.")

    try:
        image = pymupdf.Pixmap(image_bytes)
        try:
            if image.width <= 0 or image.height <= 0:
                raise ValueError("Image has invalid dimensions.")
        finally:
            del image
    except Exception as error:
        raise ValueError("Image file is unreadable or invalid.") from error

    analysis = analyze_visual(
        image_bytes,
        image_format,
        settings,
    )

    if not analysis.content.strip():
        raise ValueError("Image analysis produced no searchable content.")

    return [
        DocumentElement(
            content_type=analysis.content_type,
            content=analysis.content,
            page_number=1,
            element_index=1,
            extraction_method=f"{settings.vlm_provider}_vision",
            extraction_model=analysis.model,
        )
    ]
