"""Run the complete FP5 retrieval-to-grounded-answer command-line workflow."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace

from database import (
    database_connection,
    get_or_create_model_setting,
    save_grounded_response,
)
from llm import (
    GenerationExecution,
    build_grounded_prompt,
    estimate_generation_cost,
    estimated_generation_application_cost,
    generate_with_gemini,
)
from provenance import code_provenance
from query import SearchResult, mysql_keyword_search, semantic_search
from settings import Settings, load_settings


AnswerGenerator = Callable[[str, Settings], str | GenerationExecution]


@dataclass(frozen=True)
class AnswerResult:
    question: str
    answer: str
    sources: list[SearchResult]
    provider: str
    model: str
    retrieval_method: str
    top_k: int
    temperature: float
    top_p: float
    latency_ms: int
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    thinking_tokens: int | None
    finish_reason: str | None
    estimated_cost: float | None
    generation_cost_status: str
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
    evaluation_snapshot: dict[str, object] | None = None,
    run_code_provenance: dict[str, object] | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    model: str | None = None,
) -> AnswerResult:
    if not question.strip():
        raise ValueError("Question cannot be empty")
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")
    if retrieval_method not in {"chroma_vector", "mysql_keyword"}:
        raise ValueError(f"Unsupported retrieval method {retrieval_method!r}")

    base_settings = load_settings()
    selected_temperature = (
        base_settings.llm_temperature if temperature is None else float(temperature)
    )
    selected_top_p = base_settings.llm_top_p if top_p is None else float(top_p)
    selected_model = base_settings.llm_chat_model if model is None else str(model).strip()
    if not selected_model:
        raise ValueError("model cannot be empty")
    if not 0.0 <= selected_temperature <= 1.0:
        raise ValueError("temperature must be between 0.0 and 1.0")
    if not 0.0 <= selected_top_p <= 1.0:
        raise ValueError("top_p must be between 0.0 and 1.0")
    settings = replace(
        base_settings,
        llm_chat_model=selected_model,
        llm_temperature=selected_temperature,
        llm_top_p=selected_top_p,
    )
    started_at = time.perf_counter()
    contexts = (
        semantic_search(question, top_k, categories)
        if retrieval_method == "chroma_vector"
        else mysql_keyword_search(question, top_k, categories)
    )
    if not contexts:
        raise RuntimeError(f"{retrieval_method} returned no matching source chunks.")
    prompt = build_grounded_prompt(question, contexts)
    generated = generator(prompt, settings)
    if isinstance(generated, GenerationExecution):
        answer = generated.answer
        input_tokens = generated.input_tokens
        output_tokens = generated.output_tokens
        total_tokens = generated.total_tokens
        thinking_tokens = generated.thinking_tokens
        finish_reason = generated.finish_reason
    else:
        answer = generated
        input_tokens = None
        output_tokens = None
        total_tokens = None
        thinking_tokens = None
        finish_reason = None
    estimated_cost = estimate_generation_cost(
        input_tokens,
        output_tokens,
        settings,
        thinking_tokens=thinking_tokens,
    )
    generation_cost_status = "recorded" if estimated_cost is not None else "unavailable"
    latency_ms = round((time.perf_counter() - started_at) * 1000)

    response_id = None
    persistence_error = None
    if save:
        try:
            captured_code = run_code_provenance or code_provenance()
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
                    evaluation_snapshot=evaluation_snapshot,
                    snapshot_provenance=(
                        "captured" if evaluation_snapshot is not None else "not_applicable"
                    ),
                    code_version=str(captured_code.get("version_label", "unavailable")),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    estimated_cost=estimated_cost,
                    generation_cost_status=generation_cost_status,
                    generation_metadata={
                        "provider": settings.llm_provider,
                        "model": settings.llm_chat_model,
                        "thinking_tokens": thinking_tokens,
                        "finish_reason": finish_reason,
                        "pricing_configured": bool(
                            settings.llm_input_cost_per_million
                            or settings.llm_output_cost_per_million
                        ),
                        "code_provenance": captured_code,
                    },
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
        temperature=settings.llm_temperature,
        top_p=settings.llm_top_p,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        thinking_tokens=thinking_tokens,
        finish_reason=finish_reason,
        estimated_cost=estimated_cost,
        generation_cost_status=generation_cost_status,
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
    parser.add_argument("--model", default=settings.llm_chat_model)
    parser.add_argument("--top-k", type=int, default=settings.retrieval_top_k)
    parser.add_argument("--temperature", type=float, default=settings.llm_temperature)
    parser.add_argument("--top-p", type=float, default=settings.llm_top_p)
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
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument(
        "--allow-unknown-cost",
        action="store_true",
        help="Permit the paid call when generation pricing has not been configured.",
    )
    parser.add_argument("--max-estimated-cost", type=float, default=0.25)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Retrieve context and print the grounded prompt without calling Gemini.",
    )
    args = parser.parse_args()

    if args.top_k <= 0:
        parser.error("--top-k must be greater than zero")
    if not 0.0 <= args.temperature <= 1.0:
        parser.error("--temperature must be between 0.0 and 1.0")
    if not 0.0 <= args.top_p <= 1.0:
        parser.error("--top-p must be between 0.0 and 1.0")
    if args.max_estimated_cost < 0:
        parser.error("--max-estimated-cost cannot be negative")

    try:
        if args.dry_run:
            categories = [value.strip() for value in (args.categories or "").split(",") if value.strip()]
            prompt, contexts = dry_run(args.question, args.top_k, args.retrieval, categories)
            if args.json:
                print(
                    json.dumps(
                        {
                            "question": args.question.strip(),
                            "model": args.model,
                            "retrieval_method": args.retrieval,
                            "top_k": args.top_k,
                            "temperature": args.temperature,
                            "top_p": args.top_p,
                            "prompt": prompt,
                            "sources": [asdict(context) for context in contexts],
                        },
                        indent=2,
                    )
                )
            else:
                print(prompt)
            return

        estimated_call_cost = estimated_generation_application_cost(settings)
        if not args.allow_paid:
            parser.error("Answer generation requires --allow-paid.")
        if estimated_call_cost is None and not args.allow_unknown_cost:
            parser.error(
                "Generation cost is unknown. Configure pricing or pass "
                "--allow-unknown-cost deliberately."
            )
        if (
            estimated_call_cost is not None
            and estimated_call_cost > args.max_estimated_cost
        ):
            parser.error(
                f"Estimated cost {estimated_call_cost:.6f} exceeds "
                f"--max-estimated-cost {args.max_estimated_cost:.6f}."
            )

        result = answer_question(
            args.question,
            top_k=args.top_k,
            save=not args.no_save,
            retrieval_method=args.retrieval,
            categories=[value.strip() for value in (args.categories or "").split(",") if value.strip()],
            temperature=args.temperature,
            top_p=args.top_p,
            model=args.model,
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
        f"temperature={result.temperature} top_p={result.top_p} "
        f"latency_ms={result.latency_ms}"
    )
    if result.estimated_cost is not None:
        print(f"Generation usage: {result.total_tokens or 0} tokens, estimated_cost={result.estimated_cost:.8f}")
    else:
        print("Generation cost: unavailable (provider pricing or usage was not recorded)")
    if result.response_id is not None:
        print(f"Saved MySQL response_id={result.response_id}")
    elif result.persistence_error:
        print(f"Warning: answer was not saved: {result.persistence_error}", file=sys.stderr)

    print("Sources:")
    for source in result.sources:
        print(
            f"{source.rank}. {source.source_path} "
            f"(chunk {source.chunk_index}, "
            + (
                f"semantic_distance {source.distance:.6f}, lexical_score {source.keyword_score}, "
                f"final_score {source.retrieval_score:.6f}"
                if source.distance is not None and source.retrieval_score is not None
                else f"lexical_score {source.keyword_score}, final_score {source.retrieval_score}"
            )
            + ")"
        )


if __name__ == "__main__":
    main()
