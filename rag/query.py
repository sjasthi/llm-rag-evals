"""Query the FP5 Chroma semantic index or the keyword retrieval baseline."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

from ingest import DEFAULT_SOURCE_DIR, build_chunks
from settings import load_settings


STOPWORDS = {
    "a", "an", "and", "are", "does", "for", "in", "is", "of", "the", "to", "what", "when",
}

SEMANTIC_CANDIDATE_MINIMUM = 50
LEXICAL_RERANK_WEIGHT = 0.05


@dataclass(frozen=True)
class SearchResult:
    rank: int
    source_path: str
    category: str
    chunk_index: int
    text: str
    distance: float | None
    keyword_score: float | None
    document_id: int | None = None
    chunk_id: int | None = None
    element_id: int | None = None
    element_index: int | None = None
    page_number: int | None = None
    content_type: str | None = None
    extraction_method: str | None = None
    extraction_model: str | None = None
    source_hash: str | None = None
    original_filename: str | None = None
    retrieval_score: float | None = None
    retrieval_metadata: dict[str, Any] = field(default_factory=dict)


def retrieval_provenance(retrieval_method: str) -> dict[str, Any]:
    """Describe the exact ranking policy represented by a retrieval label."""
    if retrieval_method == "chroma_vector":
        return {
            "version": "chroma-hybrid-v1",
            "label": "Chroma semantic candidates + lexical reranking",
            "candidate_minimum": SEMANTIC_CANDIDATE_MINIMUM,
            "candidate_top_k_multiplier": 5,
            "lexical_rerank_weight": LEXICAL_RERANK_WEIGHT,
            "final_score": "semantic_distance - lexical_rerank_weight * lexical_score",
            "score_direction": "lower_is_better",
        }
    if retrieval_method == "mysql_keyword":
        return {
            "version": "mysql-fulltext-lexical-v1",
            "label": "MySQL FULLTEXT natural-language candidates + lexical reranking",
            "candidate_minimum": 50,
            "candidate_top_k_multiplier": 10,
            "fallback": "all ingested MySQL chunks when FULLTEXT returns no rows",
            "final_score": "fulltext_score + lexical_score",
            "score_direction": "higher_is_better",
        }
    if retrieval_method == "keyword":
        return {
            "version": "filesystem-lexical-v1",
            "label": "Filesystem lexical troubleshooting baseline",
            "final_score": "lexical_score",
            "score_direction": "higher_is_better",
        }
    if retrieval_method == "hybrid_rrf":
        return {
            "version": "hybrid-rrf-v1",
            "label": "ChromaDB + MySQL Reciprocal Rank Fusion",
            "fusion_constant": 60,
            "candidate_minimum": 50,
            "candidate_top_k_multiplier": 10,
            "source_methods": [
                "chroma_vector",
                "mysql_keyword",
            ],
            "score_direction": "higher_is_better",
        }
    raise ValueError(f"Unsupported retrieval method {retrieval_method!r}")


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
            source_hash=chunk.source_hash,
            retrieval_score=float(score),
            retrieval_metadata={
                **retrieval_provenance("keyword"),
                "lexical_score": score,
            },
        )
        for rank, (score, chunk) in enumerate(matches, start=1)
    ]


def mysql_keyword_search(
    question: str, top_k: int, categories: list[str] | None = None
) -> list[SearchResult]:
    """Retrieve the indexed MySQL chunk rows using FULLTEXT plus lexical reranking."""
    if not question.strip():
        raise ValueError("Question cannot be empty")
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")

    from database import database_connection

    settings = load_settings()
    normalized_categories = sorted({value.strip() for value in (categories or []) if value.strip()})
    category_clause = ""
    category_parameters: list[Any] = []
    if normalized_categories:
        placeholders = ",".join(["%s"] * len(normalized_categories))
        category_clause = f" AND d.category IN ({placeholders})"
        category_parameters = normalized_categories
    with database_connection(settings) as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                f"""SELECT c.chunk_id, c.document_id, c.chunk_index, c.chunk_text,
                      c.element_id,
                      e.element_index, e.page_number, e.content_type,
                      e.extraction_method, e.extraction_model,
                      d.source_path, d.category, d.source_hash,
                      MATCH(c.chunk_text) AGAINST (%s IN NATURAL LANGUAGE MODE) AS fulltext_score
               FROM document_chunks c
               JOIN documents d ON d.document_id=c.document_id
               LEFT JOIN document_elements e ON e.element_id=c.element_id
                   WHERE d.status='ingested'
                     {category_clause}
                     AND MATCH(c.chunk_text) AGAINST (%s IN NATURAL LANGUAGE MODE) > 0
                   ORDER BY fulltext_score DESC, c.chunk_id
                   LIMIT %s""",
                (question, *category_parameters, question, max(top_k * 10, 50)),
            )
            rows = cursor.fetchall()
            if not rows:
                # MySQL FULLTEXT can omit short terms, stopwords, or date-heavy
                # queries. The fallback still reads the authoritative MySQL
                # chunks and applies the documented deterministic lexical rule.
                cursor.execute(
                    f"""SELECT c.chunk_id, c.document_id, c.chunk_index, c.chunk_text,
                          c.element_id,
                          e.element_index, e.page_number, e.content_type,
                          e.extraction_method, e.extraction_model,
                          d.source_path, d.category, d.source_hash, 0 AS fulltext_score
                   FROM document_chunks c
                   JOIN documents d ON d.document_id=c.document_id
                   LEFT JOIN document_elements e ON e.element_id=c.element_id
                       WHERE d.status='ingested'
                         {category_clause}
                       ORDER BY c.chunk_id""",
                    tuple(category_parameters),
                )
                rows = cursor.fetchall()

    candidates: list[tuple[float, int, dict[str, Any]]] = []
    for row in rows:
        lexical = lexical_score(question, str(row["chunk_text"]))
        fulltext = float(row.get("fulltext_score") or 0.0)
        combined = fulltext + float(lexical)
        if combined > 0:
            candidates.append((combined, lexical, row))
    candidates.sort(key=lambda value: (-value[0], int(value[2]["chunk_id"])))
    return [
        SearchResult(
            rank=rank,
            source_path=str(row["source_path"]),
            category=str(row["category"]),
            chunk_index=int(row["chunk_index"]),
            text=str(row["chunk_text"]),
            distance=None,
            keyword_score=float(_lexical),
            document_id=int(row["document_id"]),
            chunk_id=int(row["chunk_id"]),
            element_id=_optional_int(row.get("element_id")),
            element_index=_optional_int(row.get("element_index")),
            page_number=_optional_int(row.get("page_number")),
            content_type=row.get("content_type"),
            extraction_method=row.get("extraction_method"),
            extraction_model=row.get("extraction_model"),
            source_hash=str(row["source_hash"]) if row.get("source_hash") else None,
            retrieval_score=combined,
            retrieval_metadata={
                **retrieval_provenance("mysql_keyword"),
                "fulltext_score": float(row.get("fulltext_score") or 0.0),
                "lexical_score": int(_lexical),
            },
        )
        for rank, (combined, _lexical, row) in enumerate(candidates[:top_k], start=1)
    ]


def semantic_search(
    question: str, top_k: int, categories: list[str] | None = None
) -> list[SearchResult]:
    from vector_store import get_collection

    collection = get_collection(load_settings())
    if collection.count() == 0:
        raise RuntimeError("The ChromaDB collection is empty. Run rag/ingest.py first.")

    candidate_count = min(
        collection.count(), max(top_k * 5, SEMANTIC_CANDIDATE_MINIMUM)
    )
    normalized_categories = sorted({value.strip() for value in (categories or []) if value.strip()})
    where: dict[str, Any] | None = None
    if len(normalized_categories) == 1:
        where = {"category": normalized_categories[0]}
    elif normalized_categories:
        where = {"category": {"$in": normalized_categories}}
    result = collection.query(
        query_texts=[question],
        n_results=candidate_count,
        include=["documents", "metadatas", "distances"],
        where=where,
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
                element_id=_optional_int(metadata.get("element_id")),
                element_index=_optional_int(metadata.get("element_index")),
                page_number=_optional_int(metadata.get("page_number")),
                content_type=metadata.get("content_type"),
                extraction_method=metadata.get("extraction_method"),
                extraction_model=metadata.get("extraction_model"),
                source_hash=(
                    str(metadata.get("source_hash"))
                    if metadata.get("source_hash")
                    else None
                ),
            )
        )
    reranked = sorted(
        candidates,
        key=lambda match: (
            (match.distance or 0.0)
            - LEXICAL_RERANK_WEIGHT * (match.keyword_score or 0)
        ),
    )[:top_k]
    output: list[SearchResult] = []
    for rank, match in enumerate(reranked, start=1):
        lexical = float(match.keyword_score or 0)
        final_score = float(match.distance or 0.0) - LEXICAL_RERANK_WEIGHT * lexical
        output.append(
            SearchResult(
                **{
                    **asdict(match),
                    "rank": rank,
                    "retrieval_score": final_score,
                    "retrieval_metadata": {
                        **retrieval_provenance("chroma_vector"),
                        "semantic_distance": match.distance,
                        "lexical_score": lexical,
                    },
                }
            )
        )
    return output

def reciprocal_rank_fusion(
    result_lists: list[list[SearchResult]],
    top_k: int,
    k: int = 60,
) -> list[SearchResult]:
    """Combine independently ranked retrieval results using RRF."""
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")
    if k <= 0:
        raise ValueError("RRF constant must be greater than zero")

    scores: dict[tuple, float] = {}
    matches: dict[tuple, SearchResult] = {}
    contributions: dict[tuple, list[dict[str, Any]]] = {}

    for method_index, results in enumerate(result_lists):
        seen_in_method: set[tuple] = set()

        for position, result in enumerate(results, start=1):
            if result.chunk_id is not None:
                key = ("chunk_id", result.chunk_id)
            else:
                key = (
                    "source",
                    result.source_path,
                    result.chunk_index,
                )

            if key in seen_in_method:
                continue

            seen_in_method.add(key)

            contribution = 1.0 / (k + position)
            scores[key] = scores.get(key, 0.0) + contribution

            contributions.setdefault(key, []).append(
                {
                    "method_index": method_index,
                    "rank": position,
                    "contribution": contribution,
                }
            )

            if key not in matches:
                matches[key] = result
            elif (
                matches[key].element_id is None
                and result.element_id is not None
            ):
                matches[key] = result

    ranked_keys = sorted(
        scores,
        key=lambda key: (-scores[key], str(key)),
    )[:top_k]

    return [
        SearchResult(
            **{
                **asdict(matches[key]),
                "rank": rank,
                "retrieval_score": scores[key],
                "retrieval_metadata": {
                    "version": "rrf-v1",
                    "label": "Reciprocal Rank Fusion",
                    "rrf_k": k,
                    "score_direction": "higher_is_better",
                    "contributions": contributions[key],
                },
            }
        )
        for rank, key in enumerate(ranked_keys, start=1)
    ]

def hybrid_rrf_search(
    question: str,
    top_k: int,
    categories: list[str] | None = None,
) -> list[SearchResult]:
    """Combine ChromaDB and MySQL retrieval using Reciprocal Rank Fusion."""
    if not question.strip():
        raise ValueError("Question cannot be empty")
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")

    candidate_count = max(top_k * 10, 50)

    chroma_results = semantic_search(
        question,
        candidate_count,
        categories,
    )
    mysql_results = mysql_keyword_search(
        question,
        candidate_count,
        categories,
    )

    return reciprocal_rank_fusion(
        [chroma_results, mysql_results],
        top_k=top_k,
        k=60,
    )

def resolve_original_filenames(
    results: list[SearchResult],
) -> list[SearchResult]:
    """Retrieve original filenames from MySQL for final search results."""
    document_ids = sorted({
        result.document_id
        for result in results
        if result.document_id is not None
    })

    if not document_ids:
        return results

    from database import database_connection

    placeholders = ", ".join(["%s"] * len(document_ids))

    with database_connection(load_settings()) as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                f"""
                SELECT document_id, original_filename
                FROM documents
                WHERE document_id IN ({placeholders})
                """,
                tuple(document_ids),
            )

            filenames = {
                int(row["document_id"]): row["original_filename"]
                for row in cursor.fetchall()
            }

    return [
        replace(
            result,
            original_filename=filenames.get(result.document_id),
        )
        for result in results
    ]

def search_with_optional_reranking(
    question: str,
    retrieval_method: str,
    top_k: int,
    categories: list[str] | None = None,
    content_reranking: bool = False,
) -> list[SearchResult]:
    """Run the selected retrieval method with optional content-aware reranking."""
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")

    candidate_count = max(top_k * 5, 20) if content_reranking else top_k

    if retrieval_method in ("chroma", "chroma_vector"):
        results = semantic_search(question, candidate_count, categories)
    elif retrieval_method in ("mysql", "mysql_keyword"):
        results = mysql_keyword_search(question, candidate_count, categories)
    elif retrieval_method in ("hybrid", "hybrid_rrf"):
        results = hybrid_rrf_search(question, candidate_count, categories)
    else:
        raise ValueError(
            f"Unsupported retrieval method: {retrieval_method}"
        )

    if content_reranking:
        from content_reranker import rerank_results
        results = rerank_results(question, results, top_k)

    return resolve_original_filenames(results)


def _optional_int(value: Any) -> int | None:
    return int(value) if value is not None else None


def main() -> None:
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Retrieve relevant Metro State source chunks.")
    parser.add_argument("question")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--retrieval", choices=("chroma", "mysql", "keyword", "hybrid"), default="chroma")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--content-reranking",
        action="store_true",
        help="Enable content-aware reranking of retrieved chunks.",
    )
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
            matches = search_with_optional_reranking(
                question=args.question,
                retrieval_method=args.retrieval,
                top_k=args.top_k,
                content_reranking=args.content_reranking,
        )
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
