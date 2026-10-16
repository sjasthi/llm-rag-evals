
"""Extract structured text and tables from Markdown documents."""

from __future__ import annotations

import re
from pathlib import Path

from pdf_processor import DocumentElement


# Markdown table separator, e.g. | --- | :---: | ---: |
_TABLE_SEPARATOR = re.compile(
    r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$"
)

_FENCE_START = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")


def _is_table_separator(line: str) -> bool:
    return bool(_TABLE_SEPARATOR.match(line))


def _is_table_start(lines: list[str], index: int) -> bool:
    return (
        index + 1 < len(lines)
        and "|" in lines[index]
        and _is_table_separator(lines[index + 1])
    )


def process_markdown(path: Path) -> list[DocumentElement]:
    """Read UTF-8 Markdown and extract ordered text/table elements."""
    path = path.resolve()

    if not path.is_file():
        raise ValueError(f"Markdown file does not exist: {path}")

    data = path.read_bytes()

    if b"\x00" in data:
        raise ValueError("Markdown file appears to contain binary data.")

    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("Markdown file must use UTF-8 encoding.") from error

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.splitlines()

    elements: list[DocumentElement] = []
    text_buffer: list[str] = []
    index = 0

    def append_element(
            content_type: str,
            content: str,
            extraction_method: str = "markdown_parser",
    ) -> None:
        content = content.strip()
        if not content:
            return

        elements.append(
            DocumentElement(
                content_type=content_type,
                content=content,
                page_number=None,
                element_index=len(elements) + 1,
                extraction_method=extraction_method,
            )
        )

    def flush_text() -> None:
        if text_buffer:
            append_element("text", "\n".join(text_buffer))
            text_buffer.clear()

    while index < len(lines):
        line = lines[index]

        # Preserve fenced code blocks as text, without interpreting
        # headings or table syntax inside the code fence.
        # Preserve regular code fences as text, but extract Mermaid
        # fences as structured diagram elements.
        fence = _FENCE_START.match(line)

        if fence:
            fence_char = fence.group(1)[0]
            fence_length = len(fence.group(1))

            # Mermaid fences use a language identifier of "mermaid".
            language = fence.group(2).strip().split(maxsplit=1)
            is_mermaid = bool(
                language and language[0].lower() == "mermaid"
            )

            fence_lines = [line]
            index += 1

            closing_fence = re.compile(
                rf"^\s{{0,3}}{re.escape(fence_char)}"
                rf"{{{fence_length},}}\s*$"
            )

            closed = False

            while index < len(lines):
                code_line = lines[index]
                fence_lines.append(code_line)
                index += 1

                if closing_fence.match(code_line):
                    closed = True
                    break

            if is_mermaid and closed:
                flush_text()

                append_element(
                    "diagram",
                    "\n".join(fence_lines),
                    extraction_method="mermaid_source",
                )
            else:
                text_buffer.extend(fence_lines)

            continue

        # Extract Markdown tables as their own elements.
        if _is_table_start(lines, index):
            flush_text()

            table_lines = [lines[index], lines[index + 1]]
            index += 2

            while index < len(lines):
                row = lines[index]

                if not row.strip() or "|" not in row:
                    break

                table_lines.append(row)
                index += 1

            append_element("table", "\n".join(table_lines))
            continue

        # Start a new text element at each Markdown heading.
        if re.match(r"^\s{0,3}#{1,6}\s+", line):
            flush_text()

        text_buffer.append(line)
        index += 1

    flush_text()

    if not elements:
        raise ValueError("Markdown document contains no extractable content.")

    return elements
