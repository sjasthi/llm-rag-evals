"""Generate one saved response per reviewed question and score that response once."""

from __future__ import annotations

import argparse
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


def create_run(dataset_id: int, name: str, limit: int | None) -> dict[str, object]:
    settings = load_settings()
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
            top_k=settings.retrieval_top_k,
            temperature=settings.llm_temperature,
            top_p=settings.llm_top_p,
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO evaluation_runs (setting_id, run_name, status, started_at, notes)
                   VALUES (%s,%s,'running',CURRENT_TIMESTAMP,%s)""",
                (setting_id, name, f"dataset_id={dataset_id}; reviewed questions only"),
            )
            run_id = int(cursor.lastrowid)
        connection.commit()

    outcomes: list[dict[str, object]] = []
    try:
        for question in questions:
            answer = answer_question(
                str(question["question_text"]),
                top_k=settings.retrieval_top_k,
                question_id=int(question["question_id"]),
                run_id=run_id,
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
    return {"run_id": run_id, "status": status, "responses": outcomes}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run reviewed FP7 questions through the fixed RAG baseline.")
    parser.add_argument("--dataset-id", type=int, required=True)
    parser.add_argument("--name", default="FP7 local baseline")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be greater than zero")
    result = create_run(args.dataset_id, args.name, args.limit)
    print(json.dumps(result, indent=2) if args.json else f"Run {result['run_id']} completed with {len(result['responses'])} responses.")


if __name__ == "__main__":
    main()
