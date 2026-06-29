"""Query the FP5 Chroma semantic index or the keyword retrieval baseline."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ingest import DEFAULT_SOURCE_DIR, build_chunks
from settings import load_settings


STOPWORDS = {
    "a", "an", "and", "are", "does", "for", "in", "is", "of", "the", "to", "what", "when",
}

SEMANTIC_CANDIDATE_MINIMUM = 20
LEXICAL_RERANK_WEIGHT = 0.05


@dataclass(frozen=True)
class SearchResult:
    rank: int
    source_path: str
    category: str
    chunk_index: int
    text: str
    distance: float | None
    keyword_score: int | None
    document_id: int | None = None
    chunk_id: int | None = None


def lexical_score(question: str, text: str) -> int:
    question_words = [word for word in re.findall(r"[a-z0-9]+", question.lower()) if word not in STOPWORDS]
    text_words = re.findall(r"[a-z0-9]+", text.lower())
    text_word_set = set(text_words)
    normalized_text = " ".join(text_words)
    terms = set(question_words)
    phrases = {
        " ".join(question_words[index : index + 2])
        for index in range(len(question_words) - 1)
    }
    return sum(1 for term in terms if term in text_word_set) + sum(
        3 for phrase in phrases if phrase in normalized_text
    )


def keyword_search(
    question: str, source_dir: Path, top_k: int, chunk_size: int, overlap: int
) -> list[SearchResult]:
    scored: list[tuple[int, Any]] = []

    for chunk in build_chunks(source_dir, chunk_size, overlap):
        score = lexical_score(question, chunk.text)
        if score > 0:
            scored.append((score, chunk))

    matches = sorted(scored, key=lambda item: item[0], reverse=True)[:top_k]
    return [
        SearchResult(
            rank=rank,
            source_path=chunk.source_path,
            category=chunk.category,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            distance=None,
            keyword_score=score,
        )
        for rank, (score, chunk) in enumerate(matches, start=1)
    ]


def semantic_search(question: str, top_k: int) -> list[SearchResult]:
    from vector_store import get_collection

    collection = get_collection(load_settings())
    if collection.count() == 0:
        raise RuntimeError("The ChromaDB collection is empty. Run rag/ingest.py first.")

    candidate_count = min(
        collection.count(), max(top_k * 5, SEMANTIC_CANDIDATE_MINIMUM)
    )
    result = collection.query(
        query_texts=[question],
        n_results=candidate_count,
        include=["documents", "metadatas", "distances"],
    )
    documents = result.get("documents") or [[]]
    metadatas = result.get("metadatas") or [[]]
    distances = result.get("distances") or [[]]

    candidates: list[SearchResult] = []
    for text, metadata, distance in zip(documents[0], metadatas[0], distances[0]):
        metadata = metadata or {}
        candidates.append(
            SearchResult(
                rank=0,
                source_path=str(metadata.get("source_path", "unknown")),
                category=str(metadata.get("category", "unknown")),
                chunk_index=int(metadata.get("chunk_index", 0)),
                text=text or "",
                distance=float(distance),
                keyword_score=lexical_score(question, text or ""),
                document_id=_optional_int(metadata.get("document_id")),
                chunk_id=_optional_int(metadata.get("chunk_id")),
            )
        )
    reranked = sorted(
        candidates,
        key=lambda match: (
            (match.distance or 0.0)
            - LEXICAL_RERANK_WEIGHT * (match.keyword_score or 0)
        ),
    )[:top_k]
    return [
        SearchResult(**{**asdict(match), "rank": rank})
        for rank, match in enumerate(reranked, start=1)
    ]


def _optional_int(value: Any) -> int | None:
    return int(value) if value is not None else None


def main() -> None:
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Retrieve relevant Metro State source chunks.")
    parser.add_argument("question")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--retrieval", choices=("chroma", "keyword"), default="chroma")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.top_k <= 0:
        parser.error("--top-k must be greater than zero")

    try:
        if args.retrieval == "keyword":
            matches = keyword_search(
                args.question,
                args.source_dir.resolve(),
                args.top_k,
                settings.chunk_size,
                settings.chunk_overlap,
            )
        else:
            matches = semantic_search(args.question, args.top_k)
    except Exception as error:
        print(f"Query failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    if args.json:
        print(json.dumps([asdict(match) for match in matches], indent=2))
        return

    if not matches:
        print("No matches found.")
        return

    for match in matches:
        metric = (
            f"distance={match.distance:.6f} lexical_score={match.keyword_score}"
            if match.distance is not None
            else f"keyword_score={match.keyword_score}"
        )
        print(
            f"{match.rank}. {metric} source={match.source_path} "
            f"category={match.category} chunk={match.chunk_index}"
        )
        print(match.text[:400].strip())
        print()


if __name__ == "__main__":
    main()
