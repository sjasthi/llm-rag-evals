"""Ingest Metro State documents into MySQL and persistent ChromaDB."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from document_loader import DocumentLoadError, LoadedDocument, SUPPORTED_TYPES, load_document
from settings import PROJECT_ROOT, load_settings


DEFAULT_SOURCE_DIR = PROJECT_ROOT / "data" / "metrostate_documents"


@dataclass(frozen=True)
class Chunk:
    source_path: str
    category: str
    chunk_index: int
    text: str
    source_hash: str
    chroma_id: str
    source_type: str = "txt"
    original_filename: str = ""


@dataclass(frozen=True)
class IngestionSummary:
    documents: int
    chunks: int
    mysql_documents: int | None
    mysql_chunks: int | None
    chroma_chunks: int | None
    chunk_size: int
    chunk_overlap: int


def read_documents(source_dir: Path) -> list[Path]:
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")
    return sorted(
        path
        for path in source_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".txt", ".pdf", ".docx"}
    )


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be zero or less than chunk_size")

    normalized = " ".join(text.split())
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = end - overlap
    return chunks


def stable_chroma_id(source_path: str, chunk_index: int) -> str:
    path_hash = hashlib.sha256(source_path.encode("utf-8")).hexdigest()[:20]
    return f"doc-{path_hash}-chunk-{chunk_index:04d}"


def build_chunks(source_dir: Path, chunk_size: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for document_path in read_documents(source_dir):
        loaded = load_document(document_path)
        relative_path = document_path.relative_to(PROJECT_ROOT).as_posix()
        category = document_path.parent.name

        for index, chunk in enumerate(chunk_text(loaded.text, chunk_size, overlap)):
            chunks.append(
                Chunk(
                    source_path=relative_path,
                    category=category,
                    chunk_index=index,
                    text=chunk,
                    source_hash=loaded.source_hash,
                    chroma_id=stable_chroma_id(relative_path, index),
                    source_type=loaded.source_type,
                    original_filename=loaded.original_filename,
                )
            )
    return chunks


def build_loaded_document_chunks(
    loaded: LoadedDocument,
    *,
    source_path: str,
    category: str,
    chunk_size: int,
    overlap: int,
) -> list[Chunk]:
    return [
        Chunk(
            source_path=source_path,
            category=category,
            chunk_index=index,
            text=text,
            source_hash=loaded.source_hash,
            chroma_id=stable_chroma_id(source_path, index),
            source_type=loaded.source_type,
            original_filename=loaded.original_filename,
        )
        for index, text in enumerate(chunk_text(loaded.text, chunk_size, overlap))
    ]


def ingest_document(
    document_path: Path,
    *,
    source_path: str,
    category: str,
    title: str,
    original_filename: str | None = None,
    chunk_size: int,
    overlap: int,
    init_schema: bool = False,
) -> tuple[int, int]:
    """Extract and replace one document in MySQL and ChromaDB."""
    settings = load_settings()
    try:
        loaded = load_document(document_path, original_filename=original_filename)
    except DocumentLoadError as error:
        from database import database_connection, initialize_schema, record_document_failure

        if init_schema:
            initialize_schema(settings)
        source_type = SUPPORTED_TYPES.get(document_path.suffix.lower(), "unknown")
        source_hash = hashlib.sha256(document_path.read_bytes()).hexdigest()
        with database_connection(settings) as connection:
            record_document_failure(
                connection,
                title=title,
                category=category,
                source_path=source_path,
                source_type=source_type,
                original_filename=Path(original_filename or document_path.name).name,
                source_hash=source_hash,
                error=str(error),
            )
        raise
    chunks = build_loaded_document_chunks(
        loaded,
        source_path=source_path,
        category=category,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    from database import (
        database_connection,
        initialize_schema,
        mark_document_failed,
        mark_document_ingested,
        upsert_document_and_chunks,
    )
    from vector_store import get_collection, replace_document_chunks

    if init_schema:
        initialize_schema(settings)
    collection = get_collection(settings)
    with database_connection(settings) as connection:
        document_id, chunk_ids = upsert_document_and_chunks(
            connection,
            title=title,
            category=category,
            source_path=source_path,
            source_type=loaded.source_type,
            original_filename=loaded.original_filename,
            source_hash=loaded.source_hash,
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            chunks=[(chunk.chunk_index, chunk.text, chunk.chroma_id) for chunk in chunks],
        )
        try:
            replace_document_chunks(
                collection,
                ids=[chunk.chroma_id for chunk in chunks],
                documents=[chunk.text for chunk in chunks],
                metadatas=[
                    {
                        "source_path": chunk.source_path,
                        "category": chunk.category,
                        "chunk_index": chunk.chunk_index,
                        "source_hash": chunk.source_hash,
                        "source_type": loaded.source_type,
                        "original_filename": loaded.original_filename,
                        "document_id": document_id,
                        "chunk_id": chunk_id,
                    }
                    for chunk, chunk_id in zip(chunks, chunk_ids)
                ],
                source_path=source_path,
            )
            mark_document_ingested(connection, document_id)
        except Exception as error:
            mark_document_failed(connection, document_id, str(error))
            raise
    return document_id, len(chunks)


def _group_chunks(chunks: list[Chunk]) -> dict[str, list[Chunk]]:
    grouped: dict[str, list[Chunk]] = {}
    for chunk in chunks:
        grouped.setdefault(chunk.source_path, []).append(chunk)
    return grouped


def ingest(
    source_dir: Path,
    chunk_size: int,
    overlap: int,
    *,
    init_schema: bool,
    skip_mysql: bool,
    skip_chroma: bool,
) -> IngestionSummary:
    if skip_mysql and skip_chroma:
        raise ValueError("Cannot use --skip-mysql and --skip-chroma together")

    settings = load_settings()
    documents = read_documents(source_dir)
    chunks = build_chunks(source_dir, chunk_size, overlap)
    grouped_chunks = _group_chunks(chunks)

    collection = None
    if not skip_chroma:
        from vector_store import get_collection

        collection = get_collection(settings)

    mysql_counts: dict[str, int] | None = None
    if skip_mysql:
        assert collection is not None
        from vector_store import replace_document_chunks

        for source_path, document_chunks in grouped_chunks.items():
            replace_document_chunks(
                collection,
                ids=[chunk.chroma_id for chunk in document_chunks],
                documents=[chunk.text for chunk in document_chunks],
                metadatas=[
                    {
                        "source_path": chunk.source_path,
                        "category": chunk.category,
                        "chunk_index": chunk.chunk_index,
                        "source_hash": chunk.source_hash,
                    }
                    for chunk in document_chunks
                ],
                source_path=source_path,
            )
    else:
        from database import (
            database_connection,
            database_counts,
            initialize_schema,
            mark_document_failed,
            mark_document_ingested,
            upsert_document_and_chunks,
        )

        if init_schema:
            initialize_schema(settings)

        with database_connection(settings) as connection:
            for document_path in documents:
                source_path = document_path.relative_to(PROJECT_ROOT).as_posix()
                document_chunks = grouped_chunks.get(source_path, [])
                source_hash = hashlib.sha256(document_path.read_bytes()).hexdigest()
                db_chunks = [
                    (chunk.chunk_index, chunk.text, chunk.chroma_id) for chunk in document_chunks
                ]
                document_id, chunk_ids = upsert_document_and_chunks(
                    connection,
                    title=document_path.stem.replace("_", " ").title(),
                    category=document_path.parent.name,
                    source_path=source_path,
                    source_type=document_chunks[0].source_type if document_chunks else document_path.suffix[1:],
                    original_filename=document_path.name,
                    source_hash=source_hash,
                    chunk_size=chunk_size,
                    chunk_overlap=overlap,
                    chunks=db_chunks,
                )

                try:
                    if collection is not None:
                        from vector_store import replace_document_chunks

                        metadatas: list[dict[str, Any]] = []
                        for chunk, chunk_id in zip(document_chunks, chunk_ids):
                            metadatas.append(
                                {
                                    "source_path": chunk.source_path,
                                    "category": chunk.category,
                                    "chunk_index": chunk.chunk_index,
                                    "source_hash": chunk.source_hash,
                                    "document_id": document_id,
                                    "chunk_id": chunk_id,
                                }
                            )
                        replace_document_chunks(
                            collection,
                            ids=[chunk.chroma_id for chunk in document_chunks],
                            documents=[chunk.text for chunk in document_chunks],
                            metadatas=metadatas,
                            source_path=source_path,
                        )
                    mark_document_ingested(connection, document_id)
                except Exception as error:
                    mark_document_failed(connection, document_id, str(error))
                    raise

            mysql_counts = database_counts(connection)

    return IngestionSummary(
        documents=len(documents),
        chunks=len(chunks),
        mysql_documents=mysql_counts["documents"] if mysql_counts else None,
        mysql_chunks=mysql_counts["document_chunks"] if mysql_counts else None,
        chroma_chunks=collection.count() if collection is not None else None,
        chunk_size=chunk_size,
        chunk_overlap=overlap,
    )


def main() -> None:
    settings = load_settings()
    parser = argparse.ArgumentParser(
        description="Ingest Metro State documents into MySQL and ChromaDB."
    )
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--chunk-size", type=int, default=settings.chunk_size)
    parser.add_argument("--overlap", type=int, default=settings.chunk_overlap)
    parser.add_argument("--init-schema", action="store_true")
    parser.add_argument("--skip-mysql", action="store_true")
    parser.add_argument("--skip-chroma", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        summary = ingest(
            args.source_dir.resolve(),
            args.chunk_size,
            args.overlap,
            init_schema=args.init_schema,
            skip_mysql=args.skip_mysql,
            skip_chroma=args.skip_chroma,
        )
    except Exception as error:
        print(f"Ingestion failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    if args.json:
        print(json.dumps(asdict(summary), indent=2))
        return

    print(
        f"Prepared {summary.chunks} chunks from {summary.documents} documents "
        f"(chunk size {summary.chunk_size}, overlap {summary.chunk_overlap})."
    )
    if summary.mysql_documents is not None:
        print(
            f"MySQL now contains {summary.mysql_documents} documents and "
            f"{summary.mysql_chunks} chunks."
        )
    if summary.chroma_chunks is not None:
        print(f"ChromaDB collection now contains {summary.chroma_chunks} embedded chunks.")


if __name__ == "__main__":
    main()
