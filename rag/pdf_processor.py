"""Process PDF files into page-aware document elements."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pymupdf
from rag.settings import Settings
from rag.visual_processor import analyze_visual

@dataclass(frozen=True)
class DocumentElement:
    """One meaningful piece of content extracted from a document."""

    content_type: str
    content: str
    page_number: int
    element_index: int
    extraction_method: str
    extraction_model: str | None = None

@dataclass(frozen=True)
class PDFImage:
    """An image discovered within a PDF."""

    page_number: int
    image_index: int
    xref: int
    width: int
    height: int

def process_pdf(
    path: Path,
    settings: Settings | None = None,
) -> list[DocumentElement]:
    """Extract text and visual elements from a PDF."""

    path = path.resolve()

    if not path.is_file():
        raise ValueError(f"PDF file does not exist: {path}")

    elements: list[DocumentElement] = []

    with pymupdf.open(path) as document:
        for page_index, page in enumerate(document):
            page_number = page_index + 1

            # Extract normal text.
            text = page.get_text("text").strip()

            if text:
                elements.append(
                    DocumentElement(
                        content_type="text",
                        content=text,
                        page_number=page_number,
                        element_index=len(elements) + 1,
                        extraction_method="pymupdf_text",
                    )
                )

            # Detect and process embedded images.
            page_images = page.get_images(full=True)

            for image_info in page_images:
                xref = image_info[0]

                if settings is None:
                    continue

                image_data = document.extract_image(xref)

                if not image_data:
                    continue

                image_bytes = image_data["image"]
                image_format = image_data["ext"]

                try:
                    analysis = analyze_visual(
                        image_bytes,
                        image_format,
                        settings,
                    )
                except Exception as error:
                    print(
                        f"Warning: visual extraction failed on page "
                        f"{page_number}, xref {xref}: {error}"
                    )
                    continue

                elements.append(
                    DocumentElement(
                        content_type=analysis.content_type,
                        content=analysis.content,
                        page_number=page_number,
                        element_index=len(elements) + 1,
                        extraction_method="gemini_vision",
                        extraction_model=analysis.model,
                    )
                )

    return elements

def find_pdf_images(path: Path) -> list[PDFImage]:
    """Find embedded images within a PDF."""

    path = path.resolve()

    if not path.is_file():
        raise ValueError(f"PDF file does not exist: {path}")

    images: list[PDFImage] = []

    with pymupdf.open(path) as document:
        for page_index, page in enumerate(document):
            page_images = page.get_images(full=True)

            for image_index, image_info in enumerate(page_images, start=1):
                xref = image_info[0]
                width = image_info[2]
                height = image_info[3]

                images.append(
                    PDFImage(
                        page_number=page_index + 1,
                        image_index=image_index,
                        xref=xref,
                        width=width,
                        height=height,
                    )
                )

    return images

def extract_pdf_image(
    path: Path,
    xref: int,
) -> tuple[bytes, str]:
    """Extract one embedded image from a PDF using its xref."""

    path = path.resolve()

    if not path.is_file():
        raise ValueError(f"PDF file does not exist: {path}")

    with pymupdf.open(path) as document:
        image_data = document.extract_image(xref)

    if not image_data:
        raise ValueError(f"Could not extract PDF image with xref {xref}.")

    return image_data["image"], image_data["ext"]