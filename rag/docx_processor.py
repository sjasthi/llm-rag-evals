
"""Extract ordered text and table elements from Word documents."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from docx.oxml.ns import qn

from settings import Settings
from visual_processor import analyze_visual

from pdf_processor import DocumentElement




def process_docx(
    path: Path,
    settings: Settings | None = None,
) -> list[DocumentElement]:
    """Extract ordered text, tables, and inline images from DOCX."""

    path = path.resolve()

    if not path.is_file():
        raise ValueError(f"DOCX file does not exist: {path}")

    try:
        document = Document(path)
    except Exception as error:
        raise ValueError("DOCX file is unreadable or invalid.") from error

    elements: list[DocumentElement] = []
    image_cache = {}

    def append_element(
        content_type: str,
        content: str,
        extraction_method: str,
        extraction_model: str | None = None,
    ) -> None:
        if not content.strip():
            return

        elements.append(
            DocumentElement(
                content_type=content_type,
                content=content.strip(),
                page_number=None,
                element_index=len(elements) + 1,
                extraction_method=extraction_method,
                extraction_model=extraction_model,
            )
        )

    for block in document.iter_inner_content():

        if isinstance(block, Paragraph):
            text_buffer = []

            def flush_text() -> None:
                if text_buffer:
                    append_element(
                        "text",
                        "".join(text_buffer),
                        "python_docx_text",
                    )
                    text_buffer.clear()

            for run in block.runs:
                # Process text and drawings in their actual XML order.
                for child in run._element:
                    if child.tag == qn("w:t"):
                        text_buffer.append(child.text or "")

                    elif child.tag == qn("w:tab"):
                        text_buffer.append("\t")

                    elif child.tag in {
                        qn("w:br"),
                        qn("w:cr"),
                    }:
                        text_buffer.append("\n")

                    elif child.tag == qn("w:drawing"):
                        flush_text()

                        for blip in child.xpath(".//a:blip"):
                            relationship_id = blip.get(qn("r:embed"))

                            if not relationship_id:
                                continue

                            image_part = document.part.related_parts.get(
                                relationship_id
                            )

                            if image_part is None:
                                continue

                            image_format = image_part.content_type.split("/")[-1]

                            if image_format not in {"png", "jpeg"}:
                                continue

                            if settings is None:
                                continue

                            if relationship_id not in image_cache:
                                try:
                                    image_cache[relationship_id] = analyze_visual(
                                        image_part.blob,
                                        image_format,
                                        settings,
                                    )
                                except Exception as error:
                                    print(
                                        "Warning: DOCX image analysis failed "
                                        f"for {relationship_id}: {error}"
                                    )
                                    continue

                            analysis = image_cache[relationship_id]

                            append_element(
                                analysis.content_type,
                                analysis.content,
                                f"{settings.vlm_provider}_vision",
                                analysis.model,
                            )

            flush_text()

        elif isinstance(block, Table):
            rows = []

            for row in block.rows:
                cells = [
                    cell.text.strip().replace("\n", " ")
                    for cell in row.cells
                ]
                rows.append(" | ".join(cells))

            append_element(
                "table",
                "\n".join(rows),
                "python_docx_table",
            )

    return elements