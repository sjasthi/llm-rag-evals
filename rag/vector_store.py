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
