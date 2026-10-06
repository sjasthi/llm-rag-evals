"""Content-aware chunking for normalized document elements."""

from __future__ import annotations

import re
from dataclasses import dataclass

from rag.pdf_processor import DocumentElement



@dataclass(frozen=True)
class ElementChunk:
    """A retrieval chunk created from a document element."""

    content: str
    content_type: str
    page_number: int
    element_index: int
    chunk_index: int
    extraction_method: str
    extraction_model: str | None = None

VISUAL_CONTENT_TYPES = {
    "chart",
    "diagram",
    "image",
    "scanned_page",
}

def chunk_element(
    element: DocumentElement,
    *,
    max_chars: int = 800,
) -> list[ElementChunk]:
    """Create retrieval chunks using rules appropriate for the element type."""

    if not element.content.strip():
        return []

    if element.content_type == "text":
        contents = chunk_text(
            element.content,
            max_chars=max_chars,
        )

    elif element.content_type == "table":
        contents = chunk_table(
            element.content,
            max_chars=max_chars,
        )

    elif element.content_type in VISUAL_CONTENT_TYPES:
        contents = [element.content.strip()]

    else:
        contents = chunk_text(
            element.content,
            max_chars=max_chars,
        )

    return [
        ElementChunk(
            content=content,
            content_type=element.content_type,
            page_number=element.page_number,
            element_index=element.element_index,
            chunk_index=chunk_index,
            extraction_method=element.extraction_method,
            extraction_model=element.extraction_model,
        )
        for chunk_index, content in enumerate(contents, start=1)
    ]

def split_sentences(text: str) -> list[str]:
    """Split text into sentences using common sentence-ending punctuation."""

    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text.strip())
        if sentence.strip()
    ]

def split_long_sentence(
    sentence: str,
    *,
    max_chars: int,
) -> list[str]:
    """Split an unusually long sentence at word boundaries."""

    words = sentence.split()

    if not words:
        return []

    chunks: list[str] = []
    current_words: list[str] = []
    current_length = 0

    for word in words:
        added_length = len(word)

        if current_words:
            added_length += 1

        if current_words and current_length + added_length > max_chars:
            chunks.append(" ".join(current_words))

            current_words = [word]
            current_length = len(word)

        else:
            current_words.append(word)
            current_length += added_length

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks

def split_oversized_paragraph(
    paragraph: str,
    *,
    max_chars: int,
) -> list[str]:
    """Split an oversized paragraph at sentence boundaries."""

    sentences = split_sentences(paragraph)

    if not sentences:
        return []

    chunks: list[str] = []
    current_sentences: list[str] = []
    current_length = 0

    expanded_sentences: list[str] = []

    for sentence in sentences:
        if len(sentence) > max_chars:
            expanded_sentences.extend(
                split_long_sentence(
                    sentence,
                    max_chars=max_chars,
                )
            )
        else:
            expanded_sentences.append(sentence)

    for sentence in expanded_sentences:
        added_length = len(sentence)

        if current_sentences:
            added_length += 1

        if current_sentences and current_length + added_length > max_chars:
            chunks.append(" ".join(current_sentences))

            overlap_sentence = current_sentences[-1]

            if len(overlap_sentence) + 1 + len(sentence) <= max_chars:
                current_sentences = [
                    overlap_sentence,
                    sentence,
                ]
                current_length = (
                        len(overlap_sentence)
                        + 1
                        + len(sentence)
                )
            else:
                current_sentences = [sentence]
                current_length = len(sentence)

        else:
            current_sentences.append(sentence)
            current_length += added_length

    if current_sentences:
        chunks.append(" ".join(current_sentences))

    return chunks

def chunk_text(
    text: str,
    *,
    max_chars: int = 800,
) -> list[str]:
    """Split text using paragraph, sentence, and word boundaries."""

    paragraphs = [
        paragraph.strip()
        for paragraph in text.split("\n\n")
        if paragraph.strip()
    ]

    if not paragraphs:
        return []

    chunks: list[str] = []
    current_paragraphs: list[str] = []
    current_length = 0

    for paragraph in paragraphs:

        if len(paragraph) > max_chars:
            if current_paragraphs:
                chunks.append("\n\n".join(current_paragraphs))
                current_paragraphs = []
                current_length = 0

            chunks.extend(
                split_oversized_paragraph(
                    paragraph,
                    max_chars=max_chars,
                )
            )

            continue

        added_length = len(paragraph)

        if current_paragraphs:
            added_length += 2

        if current_paragraphs and current_length + added_length > max_chars:
            chunks.append("\n\n".join(current_paragraphs))

            current_paragraphs = [paragraph]
            current_length = len(paragraph)

        else:
            current_paragraphs.append(paragraph)
            current_length += added_length

    if current_paragraphs:
        chunks.append("\n\n".join(current_paragraphs))

    return chunks

def chunk_table(
    text: str,
    *,
    max_chars: int = 800,
) -> list[str]:
    """Chunk a Markdown-style table by rows while repeating its header."""

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        return []

    # A Markdown table needs at least:
    # header row + separator row + one data row.
    if len(lines) < 3:
        return [text.strip()]

    header = lines[0]
    separator = lines[1]
    data_rows = lines[2:]

    header_block = f"{header}\n{separator}"

    # Small tables can remain intact.
    if len(text.strip()) <= max_chars:
        return [text.strip()]

    chunks: list[str] = []
    current_rows: list[str] = []

    for row in data_rows:
        candidate_rows = current_rows + [row]

        candidate = "\n".join(
            [header_block, *candidate_rows]
        )

        if current_rows and len(candidate) > max_chars:
            chunks.append(
                "\n".join(
                    [header_block, *current_rows]
                )
            )

            current_rows = [row]

        else:
            current_rows.append(row)

    if current_rows:
        chunks.append(
            "\n".join(
                [header_block, *current_rows]
            )
        )

    return chunks
