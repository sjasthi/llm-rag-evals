"""Run the complete FP5 retrieval-to-grounded-answer command-line workflow.

Version 2.0 adds optional conversation memory: pass ``conversation_id`` (or
``start_conversation``) to answer a follow-up using the bounded recent history
described in conversation.py. Without a conversation the workflow is the
unchanged single-turn Version 1 path used by evaluation runs.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, replace

from citation_validator import CitationValidation, validate_citations

from conversation import (
    DEFAULT_HISTORY_MESSAGES,
    UNKNOWN_CONVERSATION_EXIT_CODE,
    ConversationMessage,
    UnknownConversationError,
    append_exchange,
    bounded_history,
    create_conversation,
    load_recent_messages,
    require_conversation,
)
from database import (
    database_connection,
    get_or_create_model_setting,
    save_grounded_response,
)
from llm import (
    GenerationExecution,
    QueryRewrite,
    build_grounded_prompt,
    estimate_generation_cost,
    estimated_generation_application_cost,
    generate_grounded_answer,
    provider_for_model,
    rewrite_follow_up_query,
)
from provenance import code_provenance
from query import (
    DocumentScope,
    SearchResult,
    search_with_optional_reranking,
)

from settings import Settings, load_settings

AnswerGenerator = Callable[[str, Settings], str | GenerationExecution]
QueryRewriter = Callable[[str, Sequence[ConversationMessage], Settings], QueryRewrite]


def search_question_unchanged(
    question: str, history: Sequence[ConversationMessage], _settings: Settings
) -> QueryRewrite:
    """Rewriter for callers with a custom generator: search exactly what was asked."""
    return QueryRewrite(
        query=question.strip(), status="no_history" if not history else "not_configured"
    )

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
    citation_validation: CitationValidation | None = None
    conversation_id: int | None = None
    retrieval_query: str | None = None
    history_messages_used: int = 0
    query_rewrite_status: str = "no_history"
    saved: bool = False
    """True only when the answer (and, for Chat, its conversation turn) was committed."""


def load_conversation_history(
    conversation_id: int,
    settings: Settings,
    *,
    max_messages: int = DEFAULT_HISTORY_MESSAGES,
    user_id: int | None = None,
) -> list[ConversationMessage]:
    """Verify the conversation exists (and is owned) and return its bounded history."""
    with database_connection(settings) as connection:
        require_conversation(connection, conversation_id, user_id=user_id)
        messages = load_recent_messages(connection, conversation_id, limit=max_messages)
    return bounded_history(messages, max_messages=max_messages)


def answer_question(
    question: str,
    *,
    top_k: int,
    save: bool = True,
    generator: AnswerGenerator = generate_grounded_answer,
    question_id: int | None = None,
    run_id: int | None = None,
    retrieval_method: str = "chroma_vector",
    categories: list[str] | None = None,
    evaluation_snapshot: dict[str, object] | None = None,
    run_code_provenance: dict[str, object] | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    model: str | None = None,
    content_reranking: bool = True,
    conversation_id: int | None = None,
    start_conversation: bool = False,
    history: Sequence[ConversationMessage] | None = None,
    history_messages: int = DEFAULT_HISTORY_MESSAGES,
    user_id: int | None = None,
    query_rewriter: QueryRewriter | None = None,
    shared_documents_only: bool = False,
) -> AnswerResult:
    """Answer one question from the documents the caller may use.

    ``user_id`` limits retrieval to the shared library plus that account's
    uploads (and conversations to that account); ``shared_documents_only``
    limits it to the shared library. Neither is a trusted command-line call.
    """
    if not question.strip():
        raise ValueError("Question cannot be empty")
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")
    if retrieval_method not in {"chroma_vector", "mysql_keyword","hybrid_rrf"}:
        raise ValueError(f"Unsupported retrieval method {retrieval_method!r}")
    if conversation_id is not None and start_conversation:
        raise ValueError("Use either conversation_id or start_conversation, not both")
    if conversation_id is not None and conversation_id <= 0:
        raise ValueError("conversation_id must be a positive integer")
    if history_messages < 0:
        raise ValueError("history_messages cannot be negative")
    if user_id is not None and user_id <= 0:
        raise ValueError("user_id must be a positive integer")

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
        llm_provider=provider_for_model(selected_model),
        llm_chat_model=selected_model,
        llm_temperature=selected_temperature,
        llm_top_p=selected_top_p,
    )
    started_at = time.perf_counter()
    if history is None:
        history = (
            load_conversation_history(
                conversation_id, settings, max_messages=history_messages, user_id=user_id
            )
            if conversation_id is not None
            else []
        )
    else:
        history = bounded_history(history, max_messages=history_messages)
    # Improvement 4: the selected chat model reads the recent history and says
    # what the latest question means as a standalone search query. It only
    # chooses what to search for; facts and citations still come from the
    # retrieved documents. A custom generator (tests, scripts) gets no paid
    # rewrite call unless it also supplies a rewriter.
    if query_rewriter is None:
        query_rewriter = (
            rewrite_follow_up_query
            if generator is generate_grounded_answer
            else search_question_unchanged
        )
    rewrite = (
        query_rewriter(question, history, settings)
        if history
        else QueryRewrite(query=question.strip(), status="no_history")
    )
    retrieval_query = rewrite.query.strip() or question.strip()
    contexts = search_with_optional_reranking(
        question=retrieval_query,
        retrieval_method=retrieval_method,
        top_k=top_k,
        categories=categories,
        content_reranking=content_reranking,
        scope=DocumentScope(user_id=user_id, shared_only=shared_documents_only),
    )
    if not contexts:
        raise RuntimeError(f"{retrieval_method} returned no matching source chunks.")
    prompt = build_grounded_prompt(question, contexts, history=history)
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

    # Validate inline citations against the retrieved source ranks.
    # Report issues without modifying the generated answer.
    citation_validation = validate_citations(
        answer_text=answer,
        retrieved_sources=contexts,
    )

    estimated_cost = estimate_generation_cost(
        input_tokens,
        output_tokens,
        settings,
        thinking_tokens=thinking_tokens,
    )
    rewrite_cost = estimate_generation_cost(
        rewrite.input_tokens,
        rewrite.output_tokens,
        settings,
        thinking_tokens=rewrite.thinking_tokens,
    )
    if estimated_cost is not None and rewrite_cost is not None:
        # The follow-up rewrite is a second, small call to the same model.
        estimated_cost = round(estimated_cost + rewrite_cost, 8)
    generation_cost_status = "recorded" if estimated_cost is not None else "unavailable"
    latency_ms = round((time.perf_counter() - started_at) * 1000)

    response_id = None
    persistence_error = None
    saved = False
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
                # The answer, a new conversation and both conversation
                # messages are one transaction: either all are saved or none
                # are, so a failure never leaves a half-saved chat.
                connection.start_transaction()
                pending_response_id = save_grounded_response(
                    connection,
                    own_transaction=False,
                    setting_id=setting_id,
                    question=question.strip(),
                    answer=answer,
                    latency_ms=latency_ms,
                    contexts=contexts,
                    question_id=question_id,
                    run_id=run_id,
                    user_id=user_id,
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
                        **(
                            {
                                "conversation": {
                                    "history_messages_used": len(history),
                                    "retrieval_query": retrieval_query,
                                    "query_rewrite": {
                                        "status": rewrite.status,
                                        "input_tokens": rewrite.input_tokens,
                                        "output_tokens": rewrite.output_tokens,
                                        "estimated_cost": rewrite_cost,
                                        "error": rewrite.error,
                                    },
                                }
                            }
                            if conversation_id is not None or start_conversation
                            else {}
                        ),
                    },
                )
                try:
                    target_conversation_id = conversation_id
                    if start_conversation:
                        target_conversation_id = create_conversation(
                            connection, question.strip(), user_id=user_id, commit=False
                        )
                    if target_conversation_id is not None:
                        append_exchange(
                            connection,
                            target_conversation_id,
                            question=question.strip(),
                            answer=answer,
                            response_id=pending_response_id,
                            user_id=user_id,
                            own_transaction=False,
                        )
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
                # Only report ids that now exist in MySQL.
                response_id = pending_response_id
                conversation_id = target_conversation_id
                saved = True
        except Exception as error:
            persistence_error = str(error) or error.__class__.__name__

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
        citation_validation=citation_validation,
        conversation_id=conversation_id,
        retrieval_query=retrieval_query,
        history_messages_used=len(history),
        query_rewrite_status=rewrite.status,
        saved=saved,
    )

def dry_run(
    question: str,
    top_k: int,
    retrieval_method: str = "chroma_vector",
    categories: list[str] | None = None,
    content_reranking: bool = True,
    history: Sequence[ConversationMessage] | None = None,
    scope: DocumentScope = DocumentScope(),
) -> tuple[str, list[SearchResult], str]:
    """Build the prompt without calling the model; returns (prompt, sources, search query).

    A preview never calls a model, so a follow-up is searched exactly as typed;
    the model interprets it from the conversation when the answer is generated.
    """
    history = list(history or [])
    retrieval_query = question.strip()
    contexts = search_with_optional_reranking(
        question=retrieval_query,
        retrieval_method=retrieval_method,
        top_k=top_k,
        categories=categories,
        content_reranking=content_reranking,
        scope=scope,
    )
    return build_grounded_prompt(question, contexts, history=history), contexts, retrieval_query


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
        choices=("chroma_vector", "mysql_keyword", "hybrid_rrf"),
        default="chroma_vector",
    )
    parser.add_argument(
        "--categories",
        help="Optional comma-separated corpus category subset for a controlled variant.",
    )
    conversation_group = parser.add_mutually_exclusive_group()
    conversation_group.add_argument(
        "--conversation-id",
        type=int,
        help="Answer as a follow-up in this existing conversation.",
    )
    conversation_group.add_argument(
        "--new-conversation",
        action="store_true",
        help="Start a conversation and save this question as its first turn.",
    )
    parser.add_argument(
        "--user-id",
        type=int,
        help="Signed-in user the conversation belongs to; other users' conversations are rejected.",
    )
    parser.add_argument(
        "--shared-documents-only",
        action="store_true",
        help="Search only the shared library (used for signed-out previews).",
    )
    parser.add_argument(
        "--history-messages",
        type=int,
        default=DEFAULT_HISTORY_MESSAGES,
        help="Most recent conversation messages to use as memory.",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument(
        "--no-content-reranking",
        action="store_true",
        help="Disable content-aware reranking for baseline comparisons.",
    )
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
    if args.conversation_id is not None and args.conversation_id <= 0:
        parser.error("--conversation-id must be a positive integer")
    if args.history_messages < 0:
        parser.error("--history-messages cannot be negative")
    if args.user_id is not None and args.user_id <= 0:
        parser.error("--user-id must be a positive integer")

    try:
        if args.dry_run:
            categories = [value.strip() for value in (args.categories or "").split(",") if value.strip()]
            history = (
                load_conversation_history(
                    args.conversation_id,
                    settings,
                    max_messages=args.history_messages,
                    user_id=args.user_id,
                )
                if args.conversation_id is not None
                else []
            )
            prompt, contexts, retrieval_query = dry_run(
                args.question,
                args.top_k,
                args.retrieval,
                categories,
                content_reranking=not args.no_content_reranking,
                history=history,
                scope=DocumentScope(
                    user_id=args.user_id, shared_only=args.shared_documents_only
                ),
            )
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
                            "conversation_id": args.conversation_id,
                            "retrieval_query": retrieval_query,
                            "history_messages_used": len(history),
                        },
                        indent=2,
                    )
                )
            else:
                print(prompt)
            return

        selected_settings = replace(
            settings,
            llm_provider=provider_for_model(args.model),
            llm_chat_model=args.model,
        )
        estimated_call_cost = estimated_generation_application_cost(selected_settings)
        if estimated_call_cost is not None and args.conversation_id is not None:
            # A follow-up adds one small query-rewrite call to the same model.
            estimated_call_cost = round(estimated_call_cost * 2, 8)
        if selected_settings.llm_provider != "ollama" and not args.allow_paid:
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
            content_reranking=not args.no_content_reranking,
            conversation_id=args.conversation_id,
            start_conversation=args.new_conversation,
            history_messages=args.history_messages,
            user_id=args.user_id,
            shared_documents_only=args.shared_documents_only,
        )
    except UnknownConversationError as error:
        print(f"Answer generation failed: {error}", file=sys.stderr)
        raise SystemExit(UNKNOWN_CONVERSATION_EXIT_CODE) from error
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
    if result.persistence_error:
        print(f"Warning: answer was not saved: {result.persistence_error}", file=sys.stderr)
    if result.conversation_id is not None:
        print(
            f"Conversation {result.conversation_id}: used "
            f"{result.history_messages_used} earlier message(s); "
            f"search query: {result.retrieval_query}"
        )

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
