"""Retrieval query skeleton for the Metro State RAG evaluation project."""

from __future__ import annotations

import argparse
from pathlib import Path

from ingest import DEFAULT_SOURCE_DIR, build_chunks


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "does",
    "for",
    "in",
    "is",
    "of",
    "the",
    "to",
    "what",
    "when",
}


def keyword_search(question: str, source_dir: Path, top_k: int) -> list[tuple[int, str, str]]:
    terms = {term.lower().strip(".,?:;!()[]") for term in question.split()}
    terms = {term for term in terms if term and term not in STOPWORDS}
    normalized_question = " ".join(question.lower().split())
    question_words = [word for word in normalized_question.split() if word not in STOPWORDS]
    question_phrases = {" ".join(question_words[index : index + 2]) for index in range(len(question_words) - 1)}
    scored: list[tuple[int, str, str]] = []

    for chunk in build_chunks(source_dir, chunk_size=800, overlap=100):
        text_lower = " ".join(chunk.text.lower().split())
        score = sum(1 for term in terms if term in text_lower)
        score += sum(3 for phrase in question_phrases if phrase in text_lower)

        if score > 0:
            scored.append((score, chunk.source_path, chunk.text))

    return sorted(scored, key=lambda item: item[0], reverse=True)[:top_k]


def main() -> None:
    parser = argparse.ArgumentParser(description="Test simple source retrieval.")
    parser.add_argument("question", help="Question to search for.")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    matches = keyword_search(args.question, args.source_dir, args.top_k)

    if not matches:
        print("No keyword matches found.")
        return

    for index, (score, source_path, text) in enumerate(matches, start=1):
        excerpt = text[:300].strip()
        print(f"{index}. score={score} source={source_path}")
        print(excerpt)
        print()

    print("ChromaDB semantic retrieval will be added in FP5.")


if __name__ == "__main__":
    main()
