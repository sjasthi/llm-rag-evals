"""Generate one saved response per reviewed question and score that response once."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict

from answer import answer_question
from database import database_connection, get_or_create_model_setting
from evaluation import score_saved_response
from settings import load_settings


DEFAULT_EVALUATORS = [
    "exact_contains",
    "required_fact_coverage",
    "token_f1",
    "rouge_l",
    "semantic_similarity",
    "bertscore",
    "expected_source_accuracy",
    "refusal_correctness",
]


def create_run(
    dataset_id: int,
    name: str,
    limit: int | None,
    *,
    retrieval_method: str = "chroma_vector",
    top_k: int | None = None,
    experiment_key: str | None = None,
    baseline_run_id: int | None = None,
    corpus_variant_key: str = "full_current",
    categories: list[str] | None = None,
) -> dict[str, object]:
    settings = load_settings()
    selected_top_k = top_k or settings.retrieval_top_k
    normalized_categories = sorted({value.strip() for value in (categories or []) if value.strip()})
    with database_connection(settings) as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                """SELECT q.question_id, q.question_text
                   FROM evaluation_question_memberships m
                   JOIN evaluation_questions q ON q.question_id=m.question_id
                   WHERE m.dataset_id=%s AND q.is_active=TRUE AND q.review_status='reviewed'
                   ORDER BY m.display_order""",
                (dataset_id,),
            )
            questions = cursor.fetchall()
        if limit is not None:
            questions = questions[:limit]
        if not questions:
            raise ValueError("The selected dataset has no reviewed active questions.")
        setting_id = get_or_create_model_setting(
            connection,
            provider=settings.llm_provider,
            chat_model=settings.llm_chat_model,
            embedding_model=settings.embedding_model,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            top_k=selected_top_k,
            temperature=settings.llm_temperature,
            top_p=settings.llm_top_p,
            retrieval_method=retrieval_method,
        )
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT dataset_name, version FROM evaluation_datasets WHERE dataset_id=%s",
                (dataset_id,),
            )
            dataset = cursor.fetchone()
            cursor.execute(
                """SELECT document_id, source_path, source_hash, category
                   FROM documents WHERE status='ingested'
                   ORDER BY document_id"""
            )
            documents = [
                row for row in cursor.fetchall()
                if not normalized_categories or str(row["category"]) in normalized_categories
            ]
        manifest = [
            {
                "document_id": int(document["document_id"]),
                "source_path": str(document["source_path"]),
                "source_hash": document["source_hash"],
                "category": str(document["category"]),
            }
            for document in documents
        ]
        manifest_hash = hashlib.sha256(
            json.dumps(manifest, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        run_configuration = {
            "dataset": dataset,
            "retrieval_method": retrieval_method,
            "top_k": selected_top_k,
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "embedding_model": settings.embedding_model,
            "answer_provider": settings.llm_provider,
            "answer_model": settings.llm_chat_model,
            "temperature": settings.llm_temperature,
            "top_p": settings.llm_top_p,
            "corpus_variant_key": corpus_variant_key,
            "categories": normalized_categories,
            "document_count": len(manifest),
            "corpus_manifest_hash": manifest_hash,
            "documents": manifest,
            "evaluators": DEFAULT_EVALUATORS,
        }
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO evaluation_runs
                   (setting_id, dataset_id, baseline_run_id, run_name, experiment_key,
                    corpus_variant_key, run_configuration_json, status, started_at, notes)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,'running',CURRENT_TIMESTAMP,%s)""",
                (
                    setting_id, dataset_id, baseline_run_id, name, experiment_key,
                    corpus_variant_key, json.dumps(run_configuration),
                    "Reviewed questions only; one saved answer/context set per question.",
                ),
            )
            run_id = int(cursor.lastrowid)
        connection.commit()

    outcomes: list[dict[str, object]] = []
    try:
        for question in questions:
            answer = answer_question(
                str(question["question_text"]),
                top_k=selected_top_k,
                question_id=int(question["question_id"]),
                run_id=run_id,
                retrieval_method=retrieval_method,
                categories=normalized_categories,
            )
            if answer.response_id is None:
                raise RuntimeError(answer.persistence_error or "Generated response was not saved.")
            scores = score_saved_response(answer.response_id, DEFAULT_EVALUATORS)
            outcomes.append({
                "question_id": int(question["question_id"]),
                "response_id": answer.response_id,
                "answer": answer.answer,
                "latency_ms": answer.latency_ms,
                "scores": [asdict(score) for score in scores],
            })
        status = "completed"
    except Exception:
        status = "failed"
        raise
    finally:
        with database_connection(settings) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE evaluation_runs SET status=%s, completed_at=CURRENT_TIMESTAMP WHERE run_id=%s",
                    (status, run_id),
                )
            connection.commit()
    return {
        "run_id": run_id,
        "status": status,
        "responses": outcomes,
        "configuration": run_configuration,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run reviewed FP7 questions through the fixed RAG baseline.")
    parser.add_argument("--dataset-id", type=int, required=True)
    parser.add_argument("--name", default="FP7 local baseline")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--retrieval",
        choices=("chroma_vector", "mysql_keyword"),
        default="chroma_vector",
    )
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--experiment-key")
    parser.add_argument("--baseline-run-id", type=int)
    parser.add_argument("--corpus-variant", default="full_current")
    parser.add_argument("--categories", help="Comma-separated category subset.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be greater than zero")
    if args.top_k is not None and args.top_k <= 0:
        parser.error("--top-k must be greater than zero")
    result = create_run(
        args.dataset_id,
        args.name,
        args.limit,
        retrieval_method=args.retrieval,
        top_k=args.top_k,
        experiment_key=args.experiment_key,
        baseline_run_id=args.baseline_run_id,
        corpus_variant_key=args.corpus_variant,
        categories=[value.strip() for value in (args.categories or "").split(",") if value.strip()],
    )
    print(json.dumps(result, indent=2) if args.json else f"Run {result['run_id']} completed with {len(result['responses'])} responses.")


if __name__ == "__main__":
    main()
