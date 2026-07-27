"""Persistent ChromaDB helpers using the free local default embedding model."""

from __future__ import annotations

from typing import Any, Sequence

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from settings import Settings


def get_collection(settings: Settings) -> Collection:
    if settings.embedding_model != "all-MiniLM-L6-v2":
        raise ValueError(
            "FP5 currently supports EMBEDDING_MODEL=all-MiniLM-L6-v2 through "
            "Chroma's local DefaultEmbeddingFunction."
        )

    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(settings.chroma_path))
    return client.get_or_create_collection(
        name=settings.chroma_collection,
        embedding_function=DefaultEmbeddingFunction(),
        metadata={"embedding_model": settings.embedding_model},
    )


def replace_document_chunks(
    collection: Collection,
    *,
    ids: Sequence[str],
    documents: Sequence[str],
    metadatas: Sequence[dict[str, Any]],
    source_path: str,
) -> None:
    collection.delete(where={"source_path": source_path})
    if ids:
        collection.upsert(ids=list(ids), documents=list(documents), metadatas=list(metadatas))


def delete_source_chunks(collection: Collection, source_path: str) -> int:
    """Delete one document's vectors and fail if any stale vectors remain."""
    indexed_ids = list(collection.get(where={"source_path": source_path}, include=[]).get("ids", []))
    if indexed_ids:
        collection.delete(ids=indexed_ids)
    remaining_ids = list(collection.get(where={"source_path": source_path}, include=[]).get("ids", []))
    if remaining_ids:
        raise RuntimeError(
            f"Vector cleanup verification failed for {source_path}: "
            f"{len(remaining_ids)} old chunks remain."
        )
    return len(indexed_ids)


def delete_all_chunks(collection: Collection) -> int:
    """Delete every active vector and verify that the collection is empty."""
    indexed_ids = list(collection.get(include=[]).get("ids", []))
    if indexed_ids:
        collection.delete(ids=indexed_ids)
    remaining_ids = list(collection.get(include=[]).get("ids", []))
    if remaining_ids:
        raise RuntimeError(
            f"Vector cleanup verification failed: {len(remaining_ids)} chunks remain."
        )
    return len(indexed_ids)
