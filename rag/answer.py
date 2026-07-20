"""Run the complete FP5 retrieval-to-grounded-answer command-line workflow."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass

from database import (
    database_connection,
    get_or_create_model_setting,
    save_grounded_response,
)
from llm import build_grounded_prompt, generate_with_gemini
from query import SearchResult, mysql_keyword_search, semantic_search
from settings import Settings, load_settings


AnswerGenerator = Callable[[str, Settings], str]


@dataclass(frozen=True)
class AnswerResult:
    question: str
    answer: str
    sources: list[SearchResult]
    provider: str
    model: str
    retrieval_method: str
    top_k: int
    latency_ms: int
    response_id: int | None
    persistence_error: str | None


def answer_question(
    question: str,
    *,
    top_k: int,
    save: bool = True,
    generator: AnswerGenerator = generate_with_gemini,
    question_id: int | None = None,
    run_id: int | None = None,
    retrieval_method: str = "chroma_vector",
    categories: list[str] | None = None,
) -> AnswerResult:
    if not question.strip():
        raise ValueError("Question cannot be empty")
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")
    if retrieval_method not in {"chroma_vector", "mysql_keyword"}:
        raise ValueError(f"Unsupported retrieval method {retrieval_method!r}")

    settings = load_settings()
    started_at = time.perf_counter()
    contexts = (
        semantic_search(question, top_k, categories)
        if retrieval_method == "chroma_vector"
        else mysql_keyword_search(question, top_k, categories)
    )
    if not contexts:
        raise RuntimeError(f"{retrieval_method} returned no matching source chunks.")
    prompt = build_grounded_prompt(question, contexts)
    answer = generator(prompt, settings)
    latency_ms = round((time.perf_counter() - started_at) * 1000)

    response_id = None
    persistence_error = None
    if save:
        try:
            with database_connection(settings) as connection:
                setting_id = get_or_create_model_setting(
                    connection,
                    provider=settings.llm_provider,
                    chat_model=settings.llm_chat_model,
                    embedding_model=settings.embedding_model,
                    chunk_size=settings.chunk_size,
                    chunk_overlap=settings.chunk_overlap,
                    top_k=top_k,
                    temperature=settings.llm_temperature,
                    top_p=settings.llm_top_p,
                    retrieval_method=retrieval_method,
                )
                response_id = save_grounded_response(
                    connection,
                    setting_id=setting_id,
                    question=question.strip(),
                    answer=answer,
                    latency_ms=latency_ms,
                    contexts=contexts,
                    question_id=question_id,
                    run_id=run_id,
                    retrieval_method=retrieval_method,
                )
        except Exception as error:
            persistence_error = str(error)

    return AnswerResult(
        question=question.strip(),
        answer=answer,
        sources=contexts,
        provider=settings.llm_provider,
        model=settings.llm_chat_model,
        retrieval_method=retrieval_method,
        top_k=top_k,
        latency_ms=latency_ms,
        response_id=response_id,
        persistence_error=persistence_error,
    )


def dry_run(
    question: str,
    top_k: int,
    retrieval_method: str = "chroma_vector",
    categories: list[str] | None = None,
) -> tuple[str, list[SearchResult]]:
    contexts = (
        semantic_search(question, top_k, categories)
        if retrieval_method == "chroma_vector"
        else mysql_keyword_search(question, top_k, categories)
    )
    return build_grounded_prompt(question, contexts), contexts


def main() -> None:
    settings = load_settings()
    parser = argparse.ArgumentParser(
        description="Retrieve Metro State context and generate a grounded Gemini answer."
    )
    parser.add_argument("question")
    parser.add_argument("--top-k", type=int, default=settings.retrieval_top_k)
    parser.add_argument(
        "--retrieval",
        choices=("chroma_vector", "mysql_keyword"),
        default="chroma_vector",
    )
    parser.add_argument(
        "--categories",
        help="Optional comma-separated corpus category subset for a controlled variant.",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Retrieve context and print the grounded prompt without calling Gemini.",
    )
    args = parser.parse_args()

    if args.top_k <= 0:
        parser.error("--top-k must be greater than zero")

    try:
        if args.dry_run:
            categories = [value.strip() for value in (args.categories or "").split(",") if value.strip()]
            prompt, contexts = dry_run(args.question, args.top_k, args.retrieval, categories)
            if args.json:
                print(
                    json.dumps(
                        {
                            "question": args.question.strip(),
                            "prompt": prompt,
                            "sources": [asdict(context) for context in contexts],
                        },
                        indent=2,
                    )
                )
            else:
                print(prompt)
            return

        result = answer_question(
            args.question,
            top_k=args.top_k,
            save=not args.no_save,
            retrieval_method=args.retrieval,
            categories=[value.strip() for value in (args.categories or "").split(",") if value.strip()],
        )
    except Exception as error:
        print(f"Answer generation failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    if args.json:
        print(json.dumps(asdict(result), indent=2))
        return

    print("Answer:")
    print(result.answer)
    print()
    print(
        f"Provider: {result.provider} model={result.model} "
        f"retrieval={result.retrieval_method} top_k={result.top_k} "
        f"latency_ms={result.latency_ms}"
    )
    if result.response_id is not None:
        print(f"Saved MySQL response_id={result.response_id}")
    elif result.persistence_error:
        print(f"Warning: answer was not saved: {result.persistence_error}", file=sys.stderr)

    print("Sources:")
    for source in result.sources:
        print(
            f"{source.rank}. {source.source_path} "
            f"(chunk {source.chunk_index}, distance {source.distance:.6f})"
        )


if __name__ == "__main__":
    main()
