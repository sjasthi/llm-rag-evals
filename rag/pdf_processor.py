"""Process PDF files into page-aware document elements."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from io import StringIO
from contextlib import redirect_stdout

import pymupdf
from settings import Settings
from visual_processor import analyze_visual

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

@dataclass(frozen=True)
class PDFTable:
    """A table discovered within a PDF."""

    page_number: int
    table_index: int
    rows: tuple[tuple[str, ...], ...]

def process_pdf(
    path: Path,
    settings: Settings | None = None,
) -> list[DocumentElement]:
    """Extract text and visual elements from a PDF."""

    path = path.resolve()

    if not path.is_file():
        raise ValueError(f"PDF file does not exist: {path}")

    elements: list[DocumentElement] = []
    processed_image_xrefs: set[int] = set()

    with pymupdf.open(path) as document:
        for page_index, page in enumerate(document):
            page_number = page_index + 1

            vector_candidate = has_meaningful_vector_content(page)

            # Detect tables on the page.
            # PyMuPDF's table detector prints an optional pymupdf_layout
            # recommendation to stdout. Suppress it because admin.py uses stdout
            # as a machine-readable JSON interface for the PHP application.
            with redirect_stdout(StringIO()):
                found_tables = page.find_tables()

            valid_tables = []

            for table in found_tables.tables:
                extracted_rows = table.extract()

                normalized_rows = tuple(
                    tuple((cell or "").strip() for cell in row)
                    for row in extracted_rows
                )

                if not is_likely_real_table(normalized_rows):
                    continue

                valid_tables.append((table, normalized_rows))

            table_rects = [
                pymupdf.Rect(table.bbox)
                for table, _ in valid_tables
            ]

            # Extract normal text while excluding table regions.
            text = extract_text_outside_tables(
                page,
                table_rects,
            ).strip()

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

            # Convert validated tables into structured document elements.
            for table, normalized_rows in valid_tables:
                table_text = table_to_text(normalized_rows)

                if not table_text:
                    continue

                elements.append(
                    DocumentElement(
                        content_type="table",
                        content=table_text,
                        page_number=page_number,
                        element_index=len(elements) + 1,
                        extraction_method="pymupdf_table",
                    )
                )

            # Detect and process embedded images.
            page_images = page.get_images(full=True)

            for image_info in page_images:
                xref = image_info[0]

                if settings is None:
                    continue

                if xref in processed_image_xrefs:
                    continue

                processed_image_xrefs.add(xref)

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
            if vector_candidate and settings is not None:
                try:
                    rendered_page = render_page_for_visual_analysis(page)

                    analysis = analyze_visual(
                        rendered_page,
                        "png",
                        settings,
                    )

                except Exception as error:
                    print(
                        f"Warning: vector visual extraction failed on page "
                        f"{page_number}: {error}"
                    )

                else:
                    if analysis.content_type in {"chart", "diagram"}:
                        elements.append(
                            DocumentElement(
                                content_type=analysis.content_type,
                                content=analysis.content,
                                page_number=page_number,
                                element_index=len(elements) + 1,
                                extraction_method="gemini_vision_page_render",
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

def find_pdf_tables(path: Path) -> list[PDFTable]:
    """Find and extract structured tables from a PDF."""

    path = path.resolve()

    if not path.is_file():
        raise ValueError(f"PDF file does not exist: {path}")

    tables: list[PDFTable] = []

    with pymupdf.open(path) as document:
        for page_index, page in enumerate(document):
            page_tables = page.find_tables()

            for table_index, table in enumerate(page_tables.tables, start=1):
                extracted_rows = table.extract()

                normalized_rows = tuple(
                    tuple((cell or "").strip() for cell in row)
                    for row in extracted_rows
                )

                tables.append(
                    PDFTable(
                        page_number=page_index + 1,
                        table_index=table_index,
                        rows=normalized_rows,
                    )
                )

    return tables

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

def table_to_text(rows: tuple[tuple[str, ...], ...]) -> str:
    """Convert structured table rows into searchable Markdown-style text."""

    if not rows:
        return ""

    header = rows[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]

    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)

def extract_text_outside_tables(
    page: pymupdf.Page,
    table_rects: list[pymupdf.Rect],
) -> str:
    """Extract page text while excluding text located inside tables."""

    blocks = page.get_text("blocks")
    text_parts: list[str] = []

    for block in blocks:
        x0, y0, x1, y1, text = block[:5]
        block_rect = pymupdf.Rect(x0, y0, x1, y1)

        inside_table = any(
            block_rect.intersects(table_rect)
            for table_rect in table_rects
        )

        if inside_table:
            continue

        cleaned_text = text.strip()

        if cleaned_text:
            text_parts.append(cleaned_text)

    return "\n\n".join(text_parts)

def has_meaningful_vector_content(
    page: pymupdf.Page,
    *,
    minimum_drawings: int = 5,
) -> bool:
    """Return whether a page contains substantial vector-drawn content."""

    drawings = page.get_drawings()

    if len(drawings) < minimum_drawings:
        return False

    page_area = page.rect.width * page.rect.height

    if page_area <= 0:
        return False

    drawing_rects = [
        drawing.get("rect")
        for drawing in drawings
        if drawing.get("rect") is not None
    ]

    if not drawing_rects:
        return False

    combined_rect = pymupdf.Rect(drawing_rects[0])

    for rect in drawing_rects[1:]:
        combined_rect |= pymupdf.Rect(rect)

    drawing_area = combined_rect.width * combined_rect.height
    coverage_ratio = drawing_area / page_area

    return coverage_ratio >= 0.10

def render_page_for_visual_analysis(
    page: pymupdf.Page,
    *,
    scale: float = 2.0,
) -> bytes:
    """Render a PDF page as PNG bytes for visual analysis."""

    matrix = pymupdf.Matrix(scale, scale)

    pixmap = page.get_pixmap(
        matrix=matrix,
        alpha=False,
    )

    return pixmap.tobytes("png")

def is_likely_real_table(
    rows: tuple[tuple[str, ...], ...],
) -> bool:
    """Return whether extracted rows contain enough structure to represent a table."""

    if len(rows) < 2:
        return False

    column_count = max((len(row) for row in rows), default=0)

    if column_count < 2:
        return False

    total_cells = sum(len(row) for row in rows)

    if total_cells == 0:
        return False

    populated_cells = sum(
        1
        for row in rows
        for cell in row
        if cell.strip()
    )

    populated_ratio = populated_cells / total_cells

    return populated_ratio >= 0.25