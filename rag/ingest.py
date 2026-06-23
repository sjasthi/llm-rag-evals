"""Document ingestion skeleton for the Metro State RAG evaluation project."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "data" / "metrostate_documents"


@dataclass(frozen=True)
class Chunk:
    source_path: str
    category: str
    chunk_index: int
    text: str
    source_hash: str


def read_text_documents(source_dir: Path) -> list[Path]:
    return sorted(path for path in source_dir.rglob("*.txt") if path.is_file())


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be zero or less than chunk_size")

    normalized = " ".join(text.split())
    chunks: list[str] = []
    start = 0

    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunks.append(normalized[start:end])

        if end == len(normalized):
            break

        start = end - overlap

    return chunks


def build_chunks(source_dir: Path, chunk_size: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []

    for document_path in read_text_documents(source_dir):
        text = document_path.read_text(encoding="utf-8")
        source_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        relative_path = document_path.relative_to(PROJECT_ROOT).as_posix()
        category = document_path.parent.name

        for index, chunk in enumerate(chunk_text(text, chunk_size, overlap)):
            chunks.append(
                Chunk(
                    source_path=relative_path,
                    category=category,
                    chunk_index=index,
                    text=chunk,
                    source_hash=source_hash,
                )
            )

    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare source document chunks.")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--overlap", type=int, default=100)
    parser.add_argument("--json", action="store_true", help="Print chunk metadata as JSON.")
    args = parser.parse_args()

    chunks = build_chunks(args.source_dir, args.chunk_size, args.overlap)

    if args.json:
        print(json.dumps([asdict(chunk) for chunk in chunks], indent=2))
        return

    document_count = len(read_text_documents(args.source_dir))
    print(f"Prepared {len(chunks)} chunks from {document_count} text documents.")
    print("Embedding generation and ChromaDB persistence will be added in FP5.")


if __name__ == "__main__":
    main()
